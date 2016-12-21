import itertools
import logging

import service

logger = logging.getLogger('das-care-contact-forms-logger')

address_extractor = {
    "V1": lambda resp: resp.get('Street Address')
}[service.forms_version]


def format_responses(responses_wks):
    """Format the data in the worksheet into list of dicts

    @param responses_wks The worksheet to load data from
    @return List of row mappings from column name to cell value
    """
    # The column names are in the first row
    schema = responses_wks.row_values(1)
    row_values = responses_wks.get_all_values()[1:]

    mapped_response_data = [
        dict((
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
            sorted(formatted_resps, key=address_extractor),
            key=address_extractor
        )
    )


if __name__ == "__main__":
    responses_wks = service.main_spreadsheet.get_worksheet(0)

    formatted_resps = format_responses(responses_wks)
    grouped_resps = group_responses_by_address(formatted_resps)
