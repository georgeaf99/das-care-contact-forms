import datetime
import functools
import itertools
import logging
import re

import service

logger = logging.getLogger('das-care-contact-forms-logger')

address_extractor = {
    "V1": lambda resp: resp.get('Street Address')
}[service.forms_version]


def convert_timestamp(timestamp_string):
    """Utility function that converts a timestamp string to a datetime string

    @timestamp_string The string to create a `datetime` object from
    @return a `datetime` object
    """
    timestamp_regex = r"(?P<month>\d+)/(?P<day>\d+)/(?P<year>\d+)\s(?P<hour>\d+)\:(?P<minute>\d+)\:(?P<second>\d+)"

    match = re.search(timestamp_regex, timestamp_string)

    return datetime.datetime(**dict((
        (key, int(val))
        for key, val in match.groupdict().items()
    )))


def normalize_V1(resp):
    resp['Timestamp'] = convert_timestamp(resp['Timestamp'])

    return resp


normalize = {
    'V1': normalize_V1
}[service.forms_version]


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
        normalize(dict((
            (col_name, cell_val)
            for col_name, cell_val in zip(schema, response)
            if cell_val != ''
        )))
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


if __name__ == "__main__":
    responses_wks = service.main_spreadsheet.get_worksheet(0)

    formatted_resps = format_responses(responses_wks)
    grouped_resps = group_responses_by_address(formatted_resps)
    compressed_grouped_resps = compressed_grouped_resps(grouped_resps)
