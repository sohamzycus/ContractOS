"""ContractOS CLI — serve, parse, query, facts, bindings."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> None:
    """Entry point for the contractos CLI."""
    parser = argparse.ArgumentParser(
        prog="contractos",
        description="ContractOS — The operating system for contract intelligence",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # serve
    serve_parser = subparsers.add_parser("serve", help="Start the ContractOS API server")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    serve_parser.add_argument("--port", type=int, default=8742, help="Port to listen on")
    serve_parser.add_argument("--config", default=None, help="Path to config YAML")
    serve_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    # parse
    parse_parser = subparsers.add_parser("parse", help="Parse a contract document")
    parse_parser.add_argument("file", help="Path to .docx or .pdf file")
    parse_parser.add_argument("--output", "-o", default=None, help="Output JSON file")

    # query
    query_parser = subparsers.add_parser("query", help="Ask a question about a contract")
    query_parser.add_argument("question", help="The question to ask")
    query_parser.add_argument("--document-id", required=True, help="Document ID to query")
    query_parser.add_argument("--server", default="http://127.0.0.1:8742", help="Server URL")

    # facts
    facts_parser = subparsers.add_parser("facts", help="List facts for a document")
    facts_parser.add_argument("document_id", help="Document ID")
    facts_parser.add_argument("--server", default="http://127.0.0.1:8742", help="Server URL")
    facts_parser.add_argument("--type", default=None, help="Filter by fact type")

    # bindings
    bindings_parser = subparsers.add_parser("bindings", help="List bindings for a document")
    bindings_parser.add_argument("document_id", help="Document ID")
    bindings_parser.add_argument("--server", default="http://127.0.0.1:8742", help="Server URL")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    if args.command == "serve":
        _cmd_serve(args)
    elif args.command == "parse":
        _cmd_parse(args)
    elif args.command == "query":
        _cmd_query(args)
    elif args.command == "facts":
        _cmd_facts(args)
    elif args.command == "bindings":
        _cmd_bindings(args)


def _cmd_serve(args: argparse.Namespace) -> None:
    """Start the API server."""
    import uvicorn

    from contractos.config import load_config

    config = load_config(args.config) if args.config else None

    # Override host/port from CLI args
    host = args.host
    port = args.port

    print(f"🚀 ContractOS server starting on http://{host}:{port}")
    print(f"   Health: http://{host}:{port}/health")
    print(f"   Config: http://{host}:{port}/config")
    print(f"   Docs:   http://{host}:{port}/docs")

    uvicorn.run(
        "contractos.api.app:create_app",
        host=host,
        port=port,
        reload=args.reload,
        factory=True,
    )


def _cmd_parse(args: argparse.Namespace) -> None:
    """Parse a contract document and output extraction results."""
    from contractos.tools.fact_extractor import extract_from_file

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    print(f"📄 Parsing {file_path.name}...")
    result = extract_from_file(file_path, f"doc-cli-{file_path.stem}")

    output = {
        "file": str(file_path),
        "facts": len(result.facts),
        "clauses": len(result.clauses),
        "bindings": len(result.bindings),
        "cross_references": len(result.cross_references),
        "clause_fact_slots": len(result.clause_fact_slots),
        "fact_details": [
            {
                "fact_id": f.fact_id,
                "type": f.fact_type.value,
                "value": f.value[:100],
                "location": f.evidence.location_hint,
            }
            for f in result.facts[:50]
        ],
        "clause_details": [
            {
                "clause_id": c.clause_id,
                "type": c.clause_type.value,
                "heading": c.heading,
            }
            for c in result.clauses
        ],
        "binding_details": [
            {
                "binding_id": b.binding_id,
                "term": b.term,
                "resolves_to": b.resolves_to,
                "type": b.binding_type.value,
            }
            for b in result.bindings
        ],
    }

    json_str = json.dumps(output, indent=2)

    if args.output:
        Path(args.output).write_text(json_str)
        print(f"✅ Output written to {args.output}")
    else:
        print(json_str)

    print(f"\n📊 Summary: {len(result.facts)} facts, {len(result.clauses)} clauses, "
          f"{len(result.bindings)} bindings, {len(result.cross_references)} cross-refs")


def _cmd_query(args: argparse.Namespace) -> None:
    """Ask a question about a contract via the API."""
    import httpx

    url = f"{args.server}/query/ask"
    try:
        resp = httpx.post(
            url,
            json={"question": args.question, "document_id": args.document_id},
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()

        print(f"\n💬 Answer: {data['answer']}")
        if data.get("confidence"):
            conf = data["confidence"]
            print(f"📊 Confidence: {conf.get('label', 'unknown')} ({conf.get('value', 0):.2f})")
        if data.get("facts_referenced"):
            print(f"📎 Facts referenced: {', '.join(data['facts_referenced'])}")
        if data.get("provenance"):
            prov = data["provenance"]
            print(f"🔍 Provenance: {prov['node_count']} nodes")
            print(f"   Reasoning: {prov['reasoning_summary']}")
    except httpx.ConnectError:
        print(f"Error: Cannot connect to server at {args.server}", file=sys.stderr)
        print("Start the server with: contractos serve", file=sys.stderr)
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        print(f"Error: {e.response.status_code} — {e.response.text}", file=sys.stderr)
        sys.exit(1)


def _cmd_facts(args: argparse.Namespace) -> None:
    """List facts for a document via the API."""
    import httpx

    url = f"{args.server}/contracts/{args.document_id}/facts"
    params = {}
    if args.type:
        params["fact_type"] = args.type

    try:
        resp = httpx.get(url, params=params, timeout=10.0)
        resp.raise_for_status()
        facts = resp.json()

        print(f"\n📄 Facts for {args.document_id} ({len(facts)} total):\n")
        for f in facts:
            print(f"  [{f['fact_id']}] ({f['fact_type']}) \"{f['value'][:80]}\"")
            print(f"    Location: {f['location_hint']}")
    except httpx.ConnectError:
        print(f"Error: Cannot connect to server at {args.server}", file=sys.stderr)
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        print(f"Error: {e.response.status_code} — {e.response.text}", file=sys.stderr)
        sys.exit(1)


def _cmd_bindings(args: argparse.Namespace) -> None:
    """List bindings for a document via the API."""
    import httpx

    url = f"{args.server}/contracts/{args.document_id}/bindings"

    try:
        resp = httpx.get(url, timeout=10.0)
        resp.raise_for_status()
        bindings = resp.json()

        print(f"\n🔗 Bindings for {args.document_id} ({len(bindings)} total):\n")
        for b in bindings:
            print(f"  [{b['binding_id']}] \"{b['term']}\" → \"{b['resolves_to']}\"")
            print(f"    Type: {b['binding_type']}, Scope: {b['scope']}")
    except httpx.ConnectError:
        print(f"Error: Cannot connect to server at {args.server}", file=sys.stderr)
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        print(f"Error: {e.response.status_code} — {e.response.text}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
