import datetime
import functools
import itertools
import logging
import re

import service

logger = logging.getLogger('das-care-contact-forms-logger')

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
        "Num Dogs: {num_dogs}",
        "Num Cats: {num_cats}",
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
    timestamp_regex = r"(?P<month>\d+)/(?P<day>\d+)/(?P<year>\d+)\s(?P<hour>\d+)\:(?P<minute>\d+)\:(?P<second>\d+)"

    match = re.search(timestamp_regex, timestamp_string)

    return datetime.datetime(**dict(
        (key, int(val))
        for key, val in match.groupdict().items()
    ))


def normalize_V1(resp):
    resp['Timestamp'] = convert_timestamp(resp['Timestamp'])

    return resp


normalize = {
    'V1': normalize_V1
}[service.forms_version]

address_extractor = {
    "V1": lambda resp: resp.get('Street Address')
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
        normalize(dict(
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
                key=lambda resp: (address_extractor(resp), resp['Timestamp'])
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

        compressed_responses[address] = compressed

    return compressed_responses


def generate_reports(grouped_resps, compressed_grouped_resps):
    address_to_report = {}

    for address in grouped_resps.keys():
        report_data = {
            key: value for key, value in dict(
                address=address,
                initial_contact_date=(lambda resps: None if len(resps) == 0 else resps[0])([
                    resp["Timestamp"] for resp in grouped_resps[address]
                    if resp["Type of Contact"] == "Initial Contact"
                ]),
                care_letter_date=(lambda resps: None if len(resps) == 0 else resps[0])([
                    resp["Timestamp"] for resp in grouped_resps[address]
                    if resp["Type of Contact"] == "C.A.R.E. Letter"
                ]),
                list_of_phone_call_dates=(lambda dates: "[%s]" % ", ".join(dates) if dates else None)([
                    str(resp["Timestamp"]) for resp in grouped_resps[address]
                    if resp["Type of Contact"] == "Phone Call"
                ]),
                list_of_mail_dates=(lambda dates: "[%s]" % ", ".join(dates) if dates else None)([
                    str(resp["Timestamp"]) for resp in grouped_resps[address]
                    if resp["Type of Contact"] == "Mail/Email"
                ]),
                census_tract=compressed_grouped_resps[address]["Census Tract"],
                num_dogs=compressed_grouped_resps[address].get("How many dogs do they have?"),
                num_cats=compressed_grouped_resps[address].get("How many cats do they have?"),
                indicators=compressed_grouped_resps[address].get("Are there any indicators of animals?"),
                owner_name=compressed_grouped_resps[address].get("Name"),
                owner_phone_number=compressed_grouped_resps[address].get("Phone"),
                owner_email=compressed_grouped_resps[address].get("Email"),
                num_fixed_animals=compressed_grouped_resps[address].get("Spayed/Neutered?"),
                num_vaccinated_animals=compressed_grouped_resps[address].get("Vaccinated?"),
                num_registered_animals=compressed_grouped_resps[address].get("Registered?"),
                is_in_compliance=compressed_grouped_resps[address].get("Compliance?")
            ).items() if value
        }

        # Function helpter to attempt substitution of report data into a report element
        def attempt_substitution(report_element):
            try:
                return report_element.format(**report_data)
            except KeyError:
                return None

        # Attempt to fill in each section, removing those where no successful substituion was made
        report = "\n\n".join(filter(None, map(
            # Attempt to fill in each section of the report, removing unsuccessful substitutions
            lambda report_section: "\n".join(filter(
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
