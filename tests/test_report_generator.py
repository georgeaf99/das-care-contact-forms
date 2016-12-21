import datetime

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
        ['Street Address', 'Timestamp',          'b', 'c', 'd'],
        ['1',              '10/4/2016 11:47:55', '',  '2', '3'],
    ])

    formatted_resps = report_generator.format_responses(mock_wks)

    assert len(formatted_resps) == 1

    resp = formatted_resps[0]

    assert resp['Street Address'] == '1'
    assert resp['Timestamp'] == datetime.datetime(
        month=10, day=4, year=2016,
        hour=11, minute=47, second=55
    )

    assert resp.get('b') is None
    assert resp['c'] == '2'
    assert resp['d'] == '3'


def test_group_responses_by_address():
    mock_wks = MockWorksheet([
        ['Street Address', 'Timestamp',          'b', 'c', 'd'],
        ['address_one',    '10/4/2016 15:09:24', '',  '1', '2'],
        ['address_two',    '10/4/2016 11:47:55', '',  '3', '4'],
        ['address_one',    '12/1/2017 06:03:22', '',  '5', '6'],
    ])

    formatted_resps = report_generator.format_responses(mock_wks)
    grouped_resps = report_generator.group_responses_by_address(formatted_resps)

    assert grouped_resps == {
        "address_one": [
            {
                'Street Address': 'address_one',
                'Timestamp': datetime.datetime(
                    month=10, day=4, year=2016,
                    hour=15, minute=9, second=24
                ),
                'c': '1',
                'd': '2',
            },
            {
                'Street Address': 'address_one',
                'Timestamp': datetime.datetime(
                    month=12, day=1, year=2017,
                    hour=6, minute=3, second=22
                ),
                'c': '5',
                'd': '6',
            },
        ],
        "address_two": [
            {
                'Street Address': 'address_two',
                'Timestamp': datetime.datetime(
                    month=10, day=4, year=2016,
                    hour=11, minute=47, second=55
                ),
                'c': '3',
                'd': '4',
            },
        ],
    }


def test_compress_grouped_responses():
    mock_wks = MockWorksheet([
        ['Street Address', 'Timestamp',          'b', 'c', 'd'],
        ['address_one',    '10/4/2016 15:09:24', '',  '1', '2'],
        ['address_two',    '10/4/2016 11:47:55', '',  '3', '4'],
        ['address_one',    '12/1/2017 06:03:22', 'x', '5', '6'],
    ])

    formatted_resps = report_generator.format_responses(mock_wks)
    grouped_resps = report_generator.group_responses_by_address(formatted_resps)
    compressed_resps = report_generator.compress_grouped_responses(grouped_resps)

    assert compressed_resps == {
        "address_one": {
            'Street Address': 'address_one',
            'Timestamp': datetime.datetime(
                month=12, day=1, year=2017,
                hour=6, minute=3, second=22
            ),
            'b': 'x',
            'c': '5',
            'd': '6',
        },
        "address_two": {
            'Street Address': 'address_two',
            'Timestamp': datetime.datetime(
                month=10, day=4, year=2016,
                hour=11, minute=47, second=55
            ),
            'c': '3',
            'd': '4'
        },
    }
