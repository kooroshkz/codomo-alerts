from conftest import FakeCodomo, home

from codomo_alerts import upstream
from codomo_alerts.client import Changed, Maintenance


def statuses(checks):
    return {c.name: c.status for c in checks}


def healthy():
    return FakeCodomo([home(1), home(2, city="Rotterdam", bedrooms=2), home(3, direct=False)])


def test_healthy_site_passes():
    checks = upstream.run(healthy())
    assert all(c.status == "ok" for c in checks), checks


def test_ignored_filters_fail():
    class IgnoresBedrooms(FakeCodomo):
        def homes(self, country, params):
            return super().homes(country, {k: v for k, v in params.items() if k != "bedrooms"})

    checks = upstream.run(IgnoresBedrooms([home(1), home(2, bedrooms=2)]))
    assert statuses(checks)["Follow-up pages answer"] == "fail"


def test_site_change_fails():
    site = healthy()
    site.fail = Changed("Codomo moved or removed the homes page")
    checks = upstream.run(site)
    assert checks[0].status == "fail" and "moved" in checks[0].detail


def test_maintenance_says_it_is_temporary():
    site = healthy()
    site.fail = Maintenance("Codomo is down for maintenance")
    checks = upstream.run(site)
    assert checks[0].status == "fail" and "temporary" in checks[0].detail


def test_nothing_listed_fails():
    checks = upstream.run(FakeCodomo([home(3, direct=False)]))
    assert statuses(checks)["Homes are listed"] == "fail"


def test_new_city_is_a_notice_not_a_failure():
    site = healthy()
    site.city_list = [*site.city_list, site.city_list[0].__class__("breda", "Breda", "NL")]
    checks = upstream.run(site)
    notice = [c for c in checks if c.status == "notice"]
    assert notice and "Breda" in notice[0].detail
    assert not any(c.status == "fail" for c in checks)


def test_markdown_report():
    report = upstream.markdown([upstream.Check("A", "ok"), upstream.Check("B", "fail", "why"),
                                upstream.Check("C", "notice", "new")])
    assert "| ✅ | A |  |" in report and "| ❌ | B | why |" in report and "🆕" in report
