import copy

from tradedesk import checklist_model as cm


def _tpl():
    return cm.normalize(cm.default_template())


def _all_step_ids(t):
    return [st["id"] for s in t["sections"] for o in s["options"] for st in o["steps"]]


def _tick(ids):
    return {i: {"note": "", "confirmed": True} for i in ids}


def test_default_template_is_valid_and_stable():
    t = _tpl()
    assert any(len(s["options"]) >= 3 for s in t["sections"])
    assert cm.normalize(copy.deepcopy(t)) == t


def test_default_template_has_the_three_sections_without_any_steps():
    t = _tpl()
    got = {s["title"]: [o["title"] for o in s["options"]] for s in t["sections"]}
    assert list(got) == ["Current market phase", "What time is it?", "Psychology"]
    assert got["Current market phase"] == ["Expansion", "Retracement", "Reversal", "Consolidation"]
    assert got["What time is it?"] == ["Asia", "London open", "New York open", "New York close"]
    assert got["Psychology"] == ["Calm & focused", "Tired / slept badly", "Losing streak",
                                 "Overconfidence after a win", "Anxious / afraid to miss out"]
    assert _all_step_ids(t) == []
    ids = [s["id"] for s in t["sections"]] + [o["id"] for s in t["sections"] for o in s["options"]]
    assert len(ids) == len(set(ids))


def test_progress_only_counts_steps_of_selected_options():
    t = _tpl()
    s0, s1 = t["sections"][0], t["sections"][1]
    for k, sec in enumerate((s0, s1)):                       # the default template has no steps: give it some
        for o in sec["options"]:
            o["steps"] = [{"id": f"{o['id']}-{n}", "text": f"step {n}"} for n in range(k + 2)]
    choices = {s0["id"]: s0["options"][0]["id"], s1["id"]: s1["options"][0]["id"]}
    n = len(s0["options"][0]["steps"]) + len(s1["options"][0]["steps"])
    assert cm.evaluate(t, {}, choices)["total"] == n
    assert [x[2]["id"] for x in cm.selected_steps(t, choices)] == [
        st["id"] for st in s0["options"][0]["steps"] + s1["options"][0]["steps"]]
    other = s0["options"][1]["steps"]                      # ticks of an option that is not selected don't count
    assert cm.evaluate(t, _tick(st["id"] for st in other), choices)["checked"] == 0


def test_thresholds():
    t = {"sections": [{"id": "s", "title": "s", "options": [
        {"id": "o", "title": "o", "steps": [{"id": str(n), "text": f"t{n}"} for n in range(10)]}]}]}
    c = {"s": "o"}
    assert cm.evaluate(t, _tick(str(n) for n in range(10)), c)["verdict"] == "green"
    assert cm.evaluate(t, _tick(str(n) for n in range(8)), c)["verdict"] == "green"      # 80 %
    assert cm.evaluate(t, _tick(str(n) for n in range(6)), c)["verdict"] == "yellow"     # 60 %
    assert cm.evaluate(t, _tick(str(n) for n in range(5)), c)["verdict"] == "red"        # 50 %


def test_nothing_selected_is_none():
    assert cm.evaluate(_tpl(), {}, {})["verdict"] == "none"
    assert cm.evaluate(cm.normalize({"sections": []}), {}, {})["verdict"] == "none"


def test_coerce_old_answers():
    assert cm.coerce_answers({"a": True, "b": {"note": "n", "confirmed": True}}) == {
        "a": {"note": "", "confirmed": True}, "b": {"note": "n", "confirmed": True}}


def test_load_save_and_corrupt(tmp_path):
    p = tmp_path / "tpl.json"
    t = cm.load_template(p)
    assert p.exists() and t["sections"]
    p.write_text("{broken", encoding="utf-8")
    assert cm.load_template(p)["sections"]
    assert (tmp_path / "tpl.json.bak").exists()


def test_steps_and_options_are_cleaned():
    t = cm.normalize({"sections": [{"title": "Phase", "options": [
        {"id": "a", "title": " Retracement ", "steps": [{"id": "x", "text": " one "}, {"text": "  "}, "two", 5]},
        {"title": "   ", "steps": ["dropped"]}, "junk", {"title": "Expansion"}]}]})
    opts = t["sections"][0]["options"]
    assert [o["title"] for o in opts] == ["Retracement", "Expansion"]
    assert [s["text"] for s in opts[0]["steps"]] == ["one", "two", "5"] and opts[0]["steps"][0]["id"] == "x"
    assert opts[1]["steps"] == []


def test_upgrade_from_v03_reminder_text_keeps_ids_stable():
    old = {"sections": [{"id": "s", "title": "Phase", "options": [
        {"id": "o1", "title": "Expansion", "desc": "Determine the orange\n\nWait for a confirmation\n"}]}]}
    a, b = cm.normalize(old), cm.normalize(old)
    assert a == b                                           # same ids every time -> saved ticks keep matching
    assert [s["text"] for s in a["sections"][0]["options"][0]["steps"]] == [
        "Determine the orange", "Wait for a confirmation"]


def test_upgrade_from_v02_requirements_are_kept_as_an_option():
    old = {"threshold_green": 80, "sections": [{"id": "s", "title": "Market", "items": [
        {"id": "i1", "text": "Bias is clear", "required": True}, {"id": "i2", "text": "   "}]}]}
    t = cm.normalize(old)
    opt = t["sections"][0]["options"][0]
    assert opt["title"] == "Checklist" and [s["id"] for s in opt["steps"]] == ["i1"]
    assert "items" not in t["sections"][0] and "threshold_green" not in t


def test_old_file_is_rewritten_once_on_load(tmp_path):
    import json
    p = tmp_path / "tpl.json"
    p.write_text(json.dumps({"sections": [{"id": "s", "title": "P", "options": [
        {"id": "o", "title": "R", "desc": "a\nb"}]}]}), encoding="utf-8")
    t = cm.load_template(p)
    assert json.loads(p.read_text(encoding="utf-8")) == t


def test_options_survive_save_and_load(tmp_path):
    p = tmp_path / "tpl.json"
    t = cm.load_template(p)
    t["sections"][0]["options"].append({"id": "zz", "title": "Custom", "steps": [{"id": "q", "text": "mine"}]})
    cm.save_template(t, p)
    assert cm.load_template(p)["sections"][0]["options"][-1] == {
        "id": "zz", "title": "Custom", "steps": [{"id": "q", "text": "mine"}]}


def test_coerce_choices_drops_stale_ids():
    t = cm.normalize({"sections": [{"id": "s1", "title": "Phase", "options": [{"id": "o1", "title": "A"}]}]})
    assert cm.coerce_choices({"s1": "o1", "s1x": "o1", "s1b": "gone"}, t) == {"s1": "o1"}
    assert cm.coerce_choices({"s1": "gone"}, t) == {}
    assert cm.coerce_choices("junk") == {} and cm.coerce_choices({"a": "b"}) == {"a": "b"}
