import copy

from tradehub import checklist_model as cm


def _tpl():
    return cm.normalize(copy.deepcopy(cm.DEFAULT_TEMPLATE))


def _ans(t, ids_true):
    return {i["id"]: {"note": "x", "confirmed": i["id"] in ids_true} for i in cm.all_items(t)}


def test_required_missing_forces_no_trade():
    t = _tpl()
    optional = [i["id"] for i in cm.all_items(t) if not i["required"]]
    res = cm.evaluate(t, _ans(t, optional))
    assert res["verdict"] == "red" and not res["required_ok"]


def test_all_confirmed_is_green():
    t = _tpl()
    res = cm.evaluate(t, _ans(t, [i["id"] for i in cm.all_items(t)]))
    assert res["verdict"] == "green" and res["pct"] == 100


def test_thresholds():
    t = _tpl()
    t["sections"] = [{"id": "s", "title": "s", "items": [
        {"id": str(n), "text": f"r{n}", "required": False} for n in range(10)]}]
    assert cm.evaluate(t, _ans(t, [str(n) for n in range(8)]))["verdict"] == "green"     # 80%
    assert cm.evaluate(t, _ans(t, [str(n) for n in range(6)]))["verdict"] == "yellow"    # 60%
    assert cm.evaluate(t, _ans(t, [str(n) for n in range(5)]))["verdict"] == "red"       # 50%


def test_empty_template():
    t = cm.normalize({"sections": []})
    assert cm.evaluate(t, {})["verdict"] == "none"


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


def test_normalize_drops_empty_items_and_old_hints():
    t = cm.normalize({"sections": [{"title": "A", "items": [
        {"text": "keep", "hint": "old"}, {"text": "   "}]}]})
    assert [i["text"] for i in t["sections"][0]["items"]] == ["keep"]
    assert "hint" not in t["sections"][0]["items"][0]
