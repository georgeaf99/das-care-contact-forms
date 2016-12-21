import pytest

import report_generator


class MockWorksheet:
    def __init__(self, data):
        self._data = data

    def row_values(self, row_idx):
        return self._data[row_idx - 1]

    def get_all_values(self):
        return self._data


def test_format_responses():
    mock_wks = MockWorksheet([
        ['Street Address', 'b', 'c', 'd'],
        ['1',              '',  '2', '3'],
    ])

    formatted_resps = report_generator.format_responses(mock_wks)

    assert len(formatted_resps) == 1

    resp = formatted_resps[0]

    assert resp['Street Address'] == '1'
    assert resp.get('b') is None
    assert resp['c'] == '2'
    assert resp['d'] == '3'


def test_group_responses_by_address():
    mock_wks = MockWorksheet([
        ['Street Address', 'b', 'c', 'd'],
        ['address_one',    '',  '1', '2'],
        ['address_two',    '',  '3', '4'],
        ['address_one',    '',  '5', '6'],
    ])

    formatted_resps = report_generator.format_responses(mock_wks)
    grouped_resps = report_generator.group_responses_by_address(formatted_resps)

    assert grouped_resps == {
        "address_one": [
            {'Street Address': 'address_one', 'c': '1', 'd': '2'},
            {'Street Address': 'address_one', 'c': '5', 'd': '6'},
        ],
        "address_two": [
            {'Street Address': 'address_two', 'c': '3', 'd': '4'},
        ],
    }


def test_compress_grouped_responses():
    mock_wks = MockWorksheet([
        ['Street Address', 'b', 'c', 'd'],
        ['address_one',    '',  '1', '2'],
        ['address_two',    '',  '3', '4'],
        ['address_one',    '0',  '5', '6'],
    ])

    formatted_resps = report_generator.format_responses(mock_wks)
    grouped_resps = report_generator.group_responses_by_address(formatted_resps)

    assert grouped_resps == {
        "address_one": [
            {'Street Address': 'address_one', 'c': '1', 'd': '2'},
            {'Street Address': 'address_one', 'c': '5', 'd': '6'},
        ],
        "address_two": [
            {'Street Address': 'address_two', 'c': '3', 'd': '4'},
        ],
    }
