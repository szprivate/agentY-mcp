#!/usr/bin/env python
"""Send one message to a RUNNING agentY host and print what it did.

    python scripts/agenty_turn.py "make the cube red"
    python scripts/agenty_turn.py -c <conversation-id> "now blue"
    python scripts/agenty_turn.py --no-wait "render the shot list"     # prints the turn id
    python scripts/agenty_turn.py --status <turn-id>
    python scripts/agenty_turn.py --conversations
    python scripts/agenty_turn.py -a ref.png "restyle this like the reference"

Prints the reply text, then a short summary on stderr; ``--json`` prints the whole
structured result on stdout instead. Exit code: 0 done, 1 error/unreachable,
2 waiting (agentY asked a question or a review is open), 3 timed out.

The host URL and session token are found as described in
src/utils/agenty_host_client.py (AGENTY_HOST_URL, AGENTY_SESSION_TOKEN,
AGENTY_TOKEN_FILE, AGENTY_HOME, or ../agentY/.agenty_token).
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils import agenty_host_client as host  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("message", nargs="?", help="what to ask agentY")
    ap.add_argument("-c", "--conversation", help="continue this conversation id")
    ap.add_argument("-a", "--attach", action="append", default=[], help="a local file to attach (repeatable)")
    ap.add_argument("-t", "--title", help="name for a new conversation")
    ap.add_argument("--canvas", help='"none", "conversation" (default) or a panel client id: which canvas the turn may edit')
    ap.add_argument("--no-wait", action="store_true", help="print the turn id and return at once")
    ap.add_argument("--timeout", type=int, default=1800, help="seconds to wait (default 1800)")
    ap.add_argument("--status", metavar="TURN_ID", help="show a turn's current state")
    ap.add_argument("--conversations", action="store_true", help="list conversations")
    ap.add_argument("--json", action="store_true", help="print the full result as JSON")
    args = ap.parse_args(argv)
    try:
        if args.conversations:
            print(json.dumps(host.conversations(), indent=2))
            return 0
        if args.status:
            res = host.turn_status(args.status)
        elif args.message:
            res = host.run_turn(args.message, args.conversation, not args.no_wait,
                                args.timeout, args.attach, args.title, args.canvas)
        else:
            ap.error("a message, --status or --conversations is required")
    except host.HostError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.json or args.no_wait:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        print(res.get("reply", ""))
        calls = res.get("tool_calls", [])
        print(f"[{res.get('status')}] conversation={res.get('conversation')} turn={res.get('turn_id')} "
              f"tools={len(calls)} files={[f['path'] for f in res.get('files', [])]}", file=sys.stderr)
        if res.get("waiting"):
            print(f"waiting: {res['waiting'].get('prompt')}", file=sys.stderr)
    if res.get("timed_out"):
        return 3
    return {"done": 0, "error": 1, "waiting": 2}.get(res.get("status"), 0)


if __name__ == "__main__":
    sys.exit(main())
