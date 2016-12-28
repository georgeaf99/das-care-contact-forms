import datetime
import functools
import itertools
import logging
import re

import service

logger = logging.getLogger("das-care-contact-forms-logger")

REPORT_TEMPLATE = [
    [
        "Address: {address}",
    ],
    [
        "Initial Contact Date: {initial_contact_date}",
        "C.A.R.E. Letter Date: {care_letter_date}",
        "Phone Call Dates: {list_of_phone_call_dates}",
        "Mail Dates: {list_of_mail_dates}",
    ],
    [
        "Census Tract: {census_tract}",
    ],
    [
        "Number of Dogs: {num_dogs}",
        "Number of Cats: {num_cats}",
    ],
    [
        "Indicators: {indicators}",
    ],
    [
        "Owner Name: {owner_name}",
        "Owner Phone Number: {owner_phone_number}",
        "Owner Email: {owner_email}",
    ],
    [
        "Number of Fixed Animals: {num_fixed_animals}",
        "Number of Vaccinated Animals: {num_vaccinated_animals}",
        "Number of Registered Animals: {num_registered_animals}",
    ],
    [
        "Is In Compliance: {is_in_compliance}"
    ],
]


################
# HELPER FUNCS #
################

def convert_timestamp(timestamp_string):
    """Utility function that converts a timestamp string to a datetime string

    @timestamp_string The string to create a `datetime` object from
    @return a `datetime` object
    """
    timestamp_regex = r"(?P<month>\d+)/(?P<day>\d+)/(?P<year>\d+)(\s(?P<hour>\d+)\:(?P<minute>\d+)\:(?P<second>\d+))?"

    match = re.search(timestamp_regex, timestamp_string)

    return datetime.datetime(**dict(
        (key, int(val))
        for key, val in match.groupdict().items() if val
    ))


def normalize_resp_V1(resp):
    resp['Timestamp'] = convert_timestamp(resp['Timestamp'])
    resp['Date of Contact'] = convert_timestamp(resp['Date of Contact'])

    updated_fields = {
        'Negative Compliance?': 'Negative?',
        'Registered Animals': 'Registered?',
        'Spayed/Neutered Animals': 'Spayed/Neutered?',
        'Vaccinated Animals': 'Vaccinated?',
    }

    # Migrate the updated fields over to the new version
    for old_field, new_field in updated_fields.items():
        if resp.get(old_field):
            if resp.get(new_field):
                raise Exception("The old field and new field cannot both be present: ({old} -> {new})".format(
                    old=old_field, new=new_field,
                ))

            resp[new_field] = resp[old_field]
            del resp[old_field]

    return resp


def normalize_compressed_resp_V1(compressed_resp):
    # If the owner is in compliance, then all their animals are spayed, vaccinated, and registered
    if compressed_resp.get('Compliance?') == 'Yes':
        fields_to_be_updated = ['Spayed/Neutered?','Vaccinated?', 'Registered?']

        # Accumulate the number of animals and convert back to a string
        num_animals = str(functools.reduce(
            lambda a, x: a + int(compressed_resp.get(x, 0)),
            ['How many dogs do they have?', 'How many cats do they have?'],
            0
        ))
        compressed_resp.update({field: num_animals for field in fields_to_be_updated})

    return compressed_resp


# Normalize individual responses
normalize_resp = {
    'V1': normalize_resp_V1
}[service.forms_version]

# Normalize compressed responses
normalize_compressed_resp = {
    'V1': normalize_compressed_resp_V1
}[service.forms_version]

address_extractor = {
    'V1': lambda resp: resp.get('Street Address')
}[service.forms_version]

##########################
# REPORT GENERATOR FUNCS #
##########################

def format_responses(responses_wks):
    """Format the data in the worksheet into list of dicts

    @param responses_wks The worksheet to load data from
    @return List of row mappings from column name to cell value
    """
    # The column names are in the first row
    schema = responses_wks.row_values(1)
    row_values = responses_wks.get_all_values()[1:]

    # Map responses to the schema and normalize each response
    mapped_response_data = [
        normalize_resp(dict(
            (col_name, cell_val)
            for col_name, cell_val in zip(schema, response)
            if cell_val != ''
        ))
        for response in row_values
    ]

    # Validate that the address field is not empty
    for response in (r for r in mapped_response_data if not address_extractor(r)):
        logger.warning("The following response has been ignored because it has no address: %s" % response)
        mapped_response_data.remove(response)

    return mapped_response_data

def group_responses_by_address(formatted_resps):
    """Groups formatted responses by the address field

    @param formatted_resps The formatted responses to groupby
    @return Dictionary mapping address to all entries from that address
    """
    return dict(
        (address, list(resps))
        for address, resps in itertools.groupby(
            # Sort the responses by address and then timestamp
            sorted(
                formatted_resps,
                # Extracts a tuple that will be compared from left to right
                key=lambda resp: (address_extractor(resp), resp['Date of Contact'], resp['Timestamp'])
            ),
            key=address_extractor
        )
    )


def compress_grouped_responses(grouped_resps):
    """Compress grouped responses to dislpay the most recent information

    @param grouped_resps Responses grouped by address and sorted by timestamp to be compressed
    @return A dictionary mapping addresses to compressed responses
    """
    compressed_responses = {}
    for address, responses in grouped_resps.items():
        compressed = {}
        for resp in responses:
            compressed.update(resp)

        compressed_responses[address] = normalize_compressed_resp(compressed)

    return compressed_responses


def generate_reports(grouped_resps, compressed_grouped_resps):
    address_to_report = {}

    format_date = lambda date: date.strftime("%m/%d/%y")

    for address in grouped_resps.keys():
        report_data = {
            key: value for key, value in dict(
                address=address,
                initial_contact_date=(lambda resps: None if len(resps) == 0 else resps[0])([
                    format_date(resp['Date of Contact']) for resp in grouped_resps[address]
                    if resp['Type of Contact'] == 'Initial Contact'
                ]),
                care_letter_date=(lambda resps: None if len(resps) == 0 else resps[0])([
                    format_date(resp['Date of Contact']) for resp in grouped_resps[address]
                    if resp['Type of Contact'] == 'C.A.R.E. Letter'
                ]),
                list_of_phone_call_dates=(lambda dates: "[%s]" % ", ".join(dates) if dates else None)([
                    format_date(resp['Date of Contact']) for resp in grouped_resps[address]
                    if resp['Type of Contact'] == 'Phone Call'
                ]),
                list_of_mail_dates=(lambda dates: "[%s]" % ", ".join(dates) if dates else None)([
                    format_date(resp['Date of Contact']) for resp in grouped_resps[address]
                    if resp['Type of Contact'] == 'Mail/Email'
                ]),
                census_tract=compressed_grouped_resps[address]['Census Tract'],
                num_dogs=compressed_grouped_resps[address].get('How many dogs do they have?'),
                num_cats=compressed_grouped_resps[address].get('How many cats do they have?'),
                indicators=compressed_grouped_resps[address].get('Are there any indicators of animals?'),
                owner_name=compressed_grouped_resps[address].get('Name'),
                owner_phone_number=compressed_grouped_resps[address].get('Phone'),
                owner_email=compressed_grouped_resps[address].get('Email'),
                num_fixed_animals=compressed_grouped_resps[address].get('Spayed/Neutered?'),
                num_vaccinated_animals=compressed_grouped_resps[address].get('Vaccinated?'),
                num_registered_animals=compressed_grouped_resps[address].get('Registered?'),
                is_in_compliance=compressed_grouped_resps[address].get('Compliance?')
            ).items() if value
        }

        # Function helpter to attempt substitution of report data into a report element
        def attempt_substitution(report_element):
            try:
                return report_element.format(**report_data)
            except KeyError:
                return None

        # Attempt to fill in each section, removing those where no successful substituion was made
        report = '\n\n'.join(filter(None, map(
            # Attempt to fill in each section of the report, removing unsuccessful substitutions
            lambda report_section: '\n'.join(filter(
                None,
                map(attempt_substitution, report_section),
            )),
            REPORT_TEMPLATE,
        )))

        address_to_report[address] = report

    return address_to_report


if __name__ == "__main__":
    responses_wks = service.main_spreadsheet.get_worksheet(0)

    formatted_resps = format_responses(responses_wks)
    grouped_resps = group_responses_by_address(formatted_resps)
    compressed_grouped_resps = compress_grouped_responses(grouped_resps)

    reports = generate_reports(grouped_resps, compressed_grouped_resps)
