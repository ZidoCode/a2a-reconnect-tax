"""Tests for a2a-reconnect-tax — deterministic, no network."""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import a2a_reconnect_tax as rt


def ev(i=0, state="working", artifact_id=None, text="update"):
    if artifact_id is not None:
        res = {"kind": "artifact-update", "taskId": "t1", "contextId": "c1",
               "artifact": {"artifactId": artifact_id,
                            "parts": [{"kind": "text", "text": f"chunk {artifact_id}"}]}}
    else:
        res = {"kind": "status-update", "taskId": "t1", "contextId": "c1",
               "status": {"state": state,
                          "message": {"role": "agent",
                                      "parts": [{"kind": "text", "text": f"{text} {i}"}]}},
               "final": False}
    return {"jsonrpc": "2.0", "id": 1, "result": res}


MARK = {"reconnect": True}


class TestSplitSegments(unittest.TestCase):
    def test_no_markers(self):
        self.assertEqual(len(rt.split_segments([ev(), ev(), ev()])), 1)

    def test_one_marker(self):
        events = [ev(), ev(), MARK, ev()]
        segs = rt.split_segments(events)
        self.assertEqual(len(segs), 2)
        self.assertEqual(len(segs[0]), 2)
        self.assertEqual(len(segs[1]), 1)

    def test_dashes_marker(self):
        segs = rt.split_segments([ev(), "---", ev()])
        self.assertEqual(len(segs), 2)


class TestAudit(unittest.TestCase):
    def test_no_replay(self):
        m = rt.audit([ev(1), ev(2), MARK, ev(3)])
        self.assertEqual(m["reconnects"], 1)
        self.assertEqual(m["events_replayed"], 0)
        self.assertEqual(m["tokens_replayed"], 0)

    def test_replay_detected(self):
        events = [ev(1), ev(2), MARK, ev(1), ev(2), ev(3)]
        m = rt.audit(events)
        self.assertEqual(m["events_replayed"], 2)
        self.assertGreater(m["tokens_replayed"], 0)
        self.assertGreater(m["replay_pct"], 0)

    def test_artifact_replay_detected(self):
        events = [ev(artifact_id="a1"), MARK, ev(artifact_id="a1")]
        m = rt.audit(events)
        self.assertEqual(m["events_replayed"], 1)

    def test_distinct_events_not_replay(self):
        events = [ev(1), ev(2), MARK, ev(3), ev(4)]
        m = rt.audit(events)
        self.assertEqual(m["events_replayed"], 0)

    def test_totals_add_up(self):
        events = [ev(1), ev(2), MARK, ev(2), ev(3)]
        m = rt.audit(events)
        self.assertEqual(m["tokens_total"], m["tokens_fresh"] + m["tokens_replayed"])


class TestSimulate(unittest.TestCase):
    def setUp(self):
        self.card = {"name": "x", "description": "y" * 40, "skills": []}

    def test_more_drops_more_replay(self):
        a = rt.simulate(self.card, drops=1, stream_len=100)
        b = rt.simulate(self.card, drops=5, stream_len=100)
        self.assertGreater(b["tokens_replayed"], a["tokens_replayed"])

    def test_zero_drops_no_waste(self):
        m = rt.simulate(self.card, drops=0, stream_len=100)
        self.assertEqual(m["tokens_replayed"], 0)
        self.assertEqual(m["tokens_total"], m["tokens_base"])


class TestReport(unittest.TestCase):
    def test_report_shape(self):
        events = [ev(1), ev(2), MARK, ev(2), ev(3)]
        out, m = rt.report(events, 3.0)
        self.assertIn("tokens replayed", out)
        self.assertIn("replay share", out)
        self.assertIn("savings", out)

    def test_no_reconnects_message(self):
        out, m = rt.report([ev(1), ev(2)], 3.0)
        self.assertIn("no reconnect markers", out)


class TestEventKey(unittest.TestCase):
    def test_same_payload_same_key(self):
        e1 = ev(1)
        e2 = ev(1)
        self.assertEqual(rt.event_key(e1), rt.event_key(e2))

    def test_different_payload_different_key(self):
        self.assertNotEqual(rt.event_key(ev(1)), rt.event_key(ev(2)))


if __name__ == "__main__":
    unittest.main()
