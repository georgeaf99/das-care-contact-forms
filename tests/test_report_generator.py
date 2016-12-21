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
        ['a', 'b', 'c', 'd'],
        ['1', '',  '2', '3']
    ])

    formatted_resps = report_generator.format_responses(mock_wks)

    assert len(formatted_resps) == 1

    resp = formatted_resps[0]

    assert resp['a'] == '1'
    assert resp.get('b') is None
    assert resp['c'] == '2'
    assert resp['d'] == '3'
