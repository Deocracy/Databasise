#!/usr/bin/env python3
"""Single clock for stall scripts; tests set BAK_NOW (ISO UTC)."""
import datetime
import os
import sys


def now():
    v = os.environ.get("BAK_NOW")
    if v:
        try:
            dt = datetime.datetime.fromisoformat(v.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.timezone.utc)
            return dt.astimezone(datetime.timezone.utc)
        except ValueError:
            pass
    return datetime.datetime.now(datetime.timezone.utc)


def iso_now():
    return now().isoformat().replace("+00:00", "Z")


def main():
    print(iso_now())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
