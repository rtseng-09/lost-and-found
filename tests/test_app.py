from conftest import login


def test_home_page_lists_seed_items(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"Blue water bottle" in r.data


def test_search_and_unclaimed_filter(client):
    r = client.get("/?q=umbrella")
    assert b"Black umbrella" in r.data and b"Blue water bottle" not in r.data
    # The umbrella has been returned, so the unclaimed filter hides it.
    r = client.get("/?q=umbrella&unclaimed=1")
    assert b"Black umbrella" not in r.data


def test_posting_requires_login(client):
    r = client.get("/items/new")
    assert r.status_code == 302 and "/login" in r.headers["Location"]


def test_login_with_wrong_password_fails(client):
    r = login(client, password="nope")
    assert b"Wrong username or password." in r.data


def test_logged_in_user_can_post_item(client):
    login(client)
    r = client.post("/items/new", data={"what": "Red scarf", "place": "Chapel",
                                        "found_on": "2026-11-01", "photo_url": ""},
                    follow_redirects=True)
    assert b"Item posted." in r.data and b"Red scarf" in r.data


def test_post_rejects_bad_date(client):
    login(client)
    r = client.post("/items/new", data={"what": "Hat", "place": "Gym",
                                        "found_on": "yesterday", "photo_url": ""})
    assert b"Enter the date found as YYYY-MM-DD." in r.data


def test_cannot_mark_someone_elses_item_returned(client):
    login(client, "maya")
    # Item 3 (Student ID card) belongs to jordan.
    assert client.post("/items/3/return").status_code == 403


def test_unknown_user_page_is_404(client):
    assert client.get("/u/nobody_here").status_code == 404
