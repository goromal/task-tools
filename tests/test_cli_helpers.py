import datetime
import pytest
from task_tools.cli import parse_interval, _all_weeks_on_day


class TestParseInterval:
    def test_plain_w_returns_sunday(self):
        assert parse_interval('w') == ('w', 6)

    def test_w_sun_returns_sunday(self):
        assert parse_interval('w:sun') == ('w', 6)

    def test_w_mon_returns_monday(self):
        assert parse_interval('w:mon') == ('w', 0)

    def test_w_fri_returns_friday(self):
        assert parse_interval('w:fri') == ('w', 4)

    def test_w_sat_returns_saturday(self):
        assert parse_interval('w:sat') == ('w', 5)

    def test_case_insensitive(self):
        assert parse_interval('W:MON') == ('w', 0)

    def test_d_returns_daily(self):
        itype, _ = parse_interval('d')
        assert itype == 'd'

    def test_invalid_day_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown day token"):
            parse_interval('w:xyz')

    def test_w_tue_returns_tuesday(self):
        assert parse_interval('w:tue') == ('w', 1)

    def test_w_wed_returns_wednesday(self):
        assert parse_interval('w:wed') == ('w', 2)

    def test_w_thu_returns_thursday(self):
        assert parse_interval('w:thu') == ('w', 3)

    def test_non_w_with_day_qualifier_raises(self):
        with pytest.raises(ValueError, match="only valid for 'w' intervals"):
            parse_interval('d:mon')


class TestAllWeeksOnDay:
    def test_all_mondays_in_week_range(self):
        # 2026-06-01 is Monday
        start = datetime.datetime(2026, 6, 1)
        end = datetime.datetime(2026, 6, 22)
        result = _all_weeks_on_day(start, end, 0)  # Monday=0
        assert len(result) == 4
        for d in result:
            assert d.weekday() == 0

    def test_start_on_target_day_is_included(self):
        start = datetime.datetime(2026, 6, 1)  # Monday
        end = datetime.datetime(2026, 6, 1)
        result = _all_weeks_on_day(start, end, 0)
        assert result == [start]

    def test_no_matching_day_in_range_returns_empty(self):
        # 2026-06-01 Mon through 2026-06-06 Sat: no Sunday
        start = datetime.datetime(2026, 6, 1)
        end = datetime.datetime(2026, 6, 6)
        result = _all_weeks_on_day(start, end, 6)  # Sunday
        assert result == []

    def test_sunday_matches_old_all_sundays_behavior(self):
        # 2026-07-05 is Sunday
        start = datetime.datetime(2026, 7, 5)
        end = datetime.datetime(2026, 7, 19)
        result = _all_weeks_on_day(start, end, 6)
        assert len(result) == 3
        for d in result:
            assert d.weekday() == 6
