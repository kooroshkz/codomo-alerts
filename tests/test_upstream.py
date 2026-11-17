from conftest import FakeCodomo, home

from codomo_alerts import upstream
from codomo_alerts.client import Changed, Maintenance


def statuses(checks):
    return {c.name: c.status for c in checks}


def healthy():
    return FakeCodomo([home(1), home(2, city="Rotterdam", bedrooms=2), home(3, direct=False),
                       home(4, city="Granada", country="es", bedrooms=1, tags=["Female only"]),
                       home(5, city="Linz", country="at", bedrooms=None)])


def test_healthy_site_passes():
    checks = upstream.run(healthy())
    assert all(c.status == "ok" for c in checks), checks
    assert {"Homes in Spain can be read", "Homes in Portugal can be read", "Homes in Austria can be read"} <= {
        c.name for c in checks}


def test_a_country_that_cannot_be_read_fails():
    class BrokenAbroad(FakeCodomo):
        def homes(self, country, params):
            if country == "es":
                raise Changed("Codomo changed its homes page (no filter counts in the page)")
            return super().homes(country, params)

    site = healthy()
    checks = upstream.run(BrokenAbroad(list(site.db.values())))
    assert statuses(checks)["Homes in Spain can be read"] == "fail"
    assert statuses(checks)["Homes in Austria can be read"] == "ok"


def test_new_country_is_a_notice():
    site = healthy()
    site.city_list = [*site.city_list, site.city_list[0].__class__("berlin", "Berlin", "DE")]
    checks = upstream.run(site)
    assert {"Homes in DE can be read": "ok", "New country": "notice"}.items() <= statuses(checks).items()


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


def test_a_home_just_taken_is_not_a_change():
    class FirstGone(FakeCodomo):
        def unit(self, path):
            if not self.units:
                self.units.append(path)
                raise Changed("Codomo changed its home pages (no price details on the unit page)")
            return super().unit(path)

    site = FirstGone(list(healthy().db.values()))
    checks = upstream.run(site)
    assert statuses(checks)["Home pages can be read"] == "ok"
    assert len(site.units) == 2 and site.units[0] != site.units[1]


def test_home_pages_that_cannot_be_read_fail():
    site = healthy()
    site.unit_fail = Changed("Codomo changed its home pages (no price details on the unit page)")
    checks = upstream.run(site)
    assert statuses(checks)["Home pages can be read"] == "fail"
    assert "no price details" in next(c.detail for c in checks if c.name == "Home pages can be read")


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
