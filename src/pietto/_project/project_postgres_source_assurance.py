"""Bounded PG18 native catalog acquisition for the explicit S09 source profile.

Only this tokenizer is shared with the independent checker. Catalog nodes are
not SQL, and parsing them never evaluates a source or a function body.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

from pietto._project.project_execution import (
    ExecutionError,
    verify_postgres_adbc_deployment,
)

__all__: tuple[str, ...] = ()
MAX_OBJECTS = 128
MAX_NODES = 32768
MAX_DEPTH = 64
MAX_CATALOG_BYTES = 8 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class Node:
    tag: str
    fields: tuple

    def get(self, key):
        for name, value in self.fields:
            if name == key:
                return value
        raise ExecutionError("POSTGRES_SOURCE_NODE_FIELD")


def parse_native(text):
    """Read nodeToString's escaped tokens, lists and binary Const datums only."""
    if type(text) is not str or len(text.encode()) > MAX_CATALOG_BYTES:
        raise ExecutionError("POSTGRES_SOURCE_RESOURCE_LIMIT")
    tokens = re.findall(r"(?:\\.|[^\s{}()\[\]])+|[{}()\[\]]", text)
    if len(tokens) > MAX_NODES * 32:
        raise ExecutionError("POSTGRES_SOURCE_RESOURCE_LIMIT")
    index = count = 0

    def take(depth=0):
        nonlocal index, count
        if depth > MAX_DEPTH or count >= MAX_NODES:
            raise ExecutionError("POSTGRES_SOURCE_RESOURCE_LIMIT")
        if index >= len(tokens):
            raise ExecutionError("POSTGRES_SOURCE_NODE_TRUNCATED")
        token = tokens[index]
        index += 1
        count += 1
        if token == "{":
            if index >= len(tokens) or not re.fullmatch(
                r"[A-Z][A-Z0-9_]*", tokens[index]
            ):
                raise ExecutionError("POSTGRES_SOURCE_NODE_TAG")
            tag = tokens[index]
            index += 1
            fields = []
            while index < len(tokens) and tokens[index] != "}":
                key = tokens[index]
                if not re.fullmatch(r":[A-Za-z][A-Za-z0-9_]*", key):
                    raise ExecutionError("POSTGRES_SOURCE_NODE_FIELD")
                index += 1
                value = take(depth + 1)
                if key == ":constvalue" and type(value) is int:
                    if index >= len(tokens) or tokens[index] != "[":
                        raise ExecutionError("POSTGRES_SOURCE_CONST_DATUM")
                    value = ("datum", value, take(depth + 1))
                if any(name == key[1:] for name, _ in fields):
                    raise ExecutionError("POSTGRES_SOURCE_NODE_DUPLICATE")
                fields.append((key[1:], value))
            if index >= len(tokens):
                raise ExecutionError("POSTGRES_SOURCE_NODE_TRUNCATED")
            index += 1
            return Node(tag, tuple(fields))
        if token in ("(", "["):
            close = ")" if token == "(" else "]"
            items = []
            while index < len(tokens) and tokens[index] != close:
                items.append(take(depth + 1))
            if index >= len(tokens):
                raise ExecutionError("POSTGRES_SOURCE_NODE_TRUNCATED")
            index += 1
            if token == "[" and any(
                type(v) is not int or not -128 <= v <= 255 for v in items
            ):
                raise ExecutionError("POSTGRES_SOURCE_CONST_DATUM")
            return tuple(items)
        if token in ("}", ")", "]") or token.startswith(":"):
            raise ExecutionError("POSTGRES_SOURCE_NODE_SYNTAX")
        if token == "<>":
            return None
        if token in ("true", "false"):
            return token == "true"
        if re.fullmatch(r"-?[0-9]+", token):
            if len(token) > 20:
                raise ExecutionError("POSTGRES_SOURCE_RESOURCE_LIMIT")
            return int(token)
        return re.sub(r"\\(.)", r"\1", token)

    result = take()
    if index != len(tokens):
        raise ExecutionError("POSTGRES_SOURCE_NODE_TRAILING")
    return result


def nodes(value, path=()):
    if type(value) is Node:
        yield path, value
        for key, child in value.fields:
            yield from nodes(child, path + (key,))
    elif type(value) is tuple:
        for i, child in enumerate(value):
            yield from nodes(child, path + (i,))


RESOLVE_SQL = "SELECT c.oid::bigint FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=$1 AND c.relname=$2"
RELATION_SQL = "SELECT c.oid::bigint,n.nspname::text,c.relname::text,c.relkind::text,c.relpersistence::text,c.relowner::bigint,c.relrowsecurity,c.relforcerowsecurity,c.reloptions::text,c.relam::bigint,a.amname::text,a.amhandler::bigint,EXISTS(SELECT 1 FROM pg_catalog.pg_depend d WHERE d.classid='pg_catalog.pg_class'::regclass AND d.objid=c.oid AND d.deptype='e') FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace LEFT JOIN pg_catalog.pg_am a ON a.oid=c.relam WHERE c.oid=$1::oid"
ATTR_SQL = "SELECT a.attnum::integer,a.attname::text,a.atttypid::bigint,a.attcollation::bigint,a.attgenerated::text,CASE WHEN a.attgenerated='v' THEN d.adbin::text ELSE NULL END FROM pg_catalog.pg_attribute a LEFT JOIN pg_catalog.pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum WHERE a.attrelid=$1::oid AND a.attnum>0 AND NOT a.attisdropped ORDER BY a.attnum"
CHILDREN_SQL = "SELECT inhrelid::bigint,inhseqno::integer,inhdetachpending FROM pg_catalog.pg_inherits WHERE inhparent=$1::oid ORDER BY inhseqno,inhrelid"
REWRITE_SQL = "SELECT oid::bigint,rulename::text,ev_type::text,is_instead,ev_qual::text,ev_action::text FROM pg_catalog.pg_rewrite WHERE ev_class=$1::oid AND ev_type='1' ORDER BY oid"
PROC_SQL = "SELECT p.oid::bigint,n.nspname::text,p.proname::text,l.lanname::text,p.prosrc,p.probin,p.proargtypes::text,p.prorettype::bigint,p.provolatile::text,p.prosecdef,p.prokind::text,p.proretset,p.proconfig::text,p.provariadic::bigint,EXISTS(SELECT 1 FROM pg_catalog.pg_depend d WHERE d.classid='pg_catalog.pg_proc'::regclass AND d.objid=p.oid AND d.deptype='e') FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace JOIN pg_catalog.pg_language l ON l.oid=p.prolang WHERE p.oid=$1::oid"
TYPE_SQL = "SELECT t.oid::bigint,n.nspname::text,t.typname::text,t.typtype::text,t.typbasetype::bigint,t.typelem::bigint,t.typinput::bigint,t.typoutput::bigint,t.typreceive::bigint,t.typsend::bigint,EXISTS(SELECT 1 FROM pg_catalog.pg_depend d WHERE d.classid='pg_catalog.pg_type'::regclass AND d.objid=t.oid AND d.deptype='e') FROM pg_catalog.pg_type t JOIN pg_catalog.pg_namespace n ON n.oid=t.typnamespace WHERE t.oid=$1::oid"
OP_SQL = "SELECT o.oid::bigint,n.nspname::text,o.oprname::text,o.oprleft::bigint,o.oprright::bigint,o.oprresult::bigint,o.oprcode::bigint,EXISTS(SELECT 1 FROM pg_catalog.pg_depend d WHERE d.classid='pg_catalog.pg_operator'::regclass AND d.objid=o.oid AND d.deptype='e') FROM pg_catalog.pg_operator o JOIN pg_catalog.pg_namespace n ON n.oid=o.oprnamespace WHERE o.oid=$1::oid"
COLLATION_SQL = "SELECT c.oid::bigint,n.nspname::text,c.collname::text,c.collprovider::text,c.collisdeterministic,c.collencoding,EXISTS(SELECT 1 FROM pg_catalog.pg_depend d WHERE d.classid='pg_catalog.pg_collation'::regclass AND d.objid=c.oid AND d.deptype='e') FROM pg_catalog.pg_collation c JOIN pg_catalog.pg_namespace n ON n.oid=c.collnamespace WHERE c.oid=$1::oid"
ROLE_SQL = "SELECT oid::bigint,rolname::text,rolsuper,rolinherit,rolbypassrls FROM pg_catalog.pg_roles WHERE oid=$1::oid"
MEMBERS_SQL = "SELECT roleid::bigint,member::bigint,grantor::bigint,admin_option,inherit_option,set_option FROM pg_catalog.pg_auth_members WHERE member=$1::oid ORDER BY roleid,grantor"
SQL = {
    "members": MEMBERS_SQL,
    "resolve": RESOLVE_SQL,
    "relation": RELATION_SQL,
    "attributes": ATTR_SQL,
    "children": CHILDREN_SQL,
    "rewrite": REWRITE_SQL,
    "function": PROC_SQL,
    "type": TYPE_SQL,
    "operator": OP_SQL,
    "collation": COLLATION_SQL,
    "role": ROLE_SQL,
}


@dataclass(frozen=True, slots=True)
class CatalogReply:
    kind: str
    arguments: tuple
    rows: tuple = field(repr=False)
    native: Any = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True, eq=False)
class SourceQualification:
    owner: Any = field(repr=False)
    request: Any = field(repr=False)
    context: tuple
    roots: tuple
    replies: tuple = field(repr=False)
    paths: tuple = field(repr=False)
    state: tuple = field(repr=False)
    definition_stability: str = "EXPLICIT_MANAGED_DEPLOYMENT_PREMISE"
    premise_compliance: str = "NOT_INDEPENDENTLY_VERIFIED"
    native_lifetime_protection: str = "NOT_DEMONSTRATED"

    def verify(self, owner):
        from pietto._project.project_execution_postgres_adbc import (
            PostgresADBCExecution,
        )

        if (
            type(owner) is not PostgresADBCExecution
            or self.owner is not owner
            or self.request is not owner.request
            or owner._qualification is not self
            or owner._owned_qualification is not self
            or owner._closed
            or owner._transaction != "OPEN"
            or self.context != owner.context
            or self.state != (self.roots, reply_state(self.replies), self.paths)
            or self.definition_stability != "EXPLICIT_MANAGED_DEPLOYMENT_PREMISE"
            or self.premise_compliance != "NOT_INDEPENDENTLY_VERIFIED"
            or self.native_lifetime_protection != "NOT_DEMONSTRATED"
        ):
            raise ExecutionError("POSTGRES_SOURCE_QUALIFICATION_IDENTITY")
        owner._checkpoint()
        owner._check_connection()
        verify_postgres_adbc_deployment(owner.request)


def qualify_sources(owner):
    """Metadata discovery only. A separate checker decides admissibility."""
    from pietto._project.project_postgres_source_assurance_verification import (
        verify_catalog,
    )

    verify_postgres_adbc_deployment(owner.request)
    requirements = owner.requirements
    roots = tuple((s.namespace, s.name) for s in owner.request.artifact.request.sources)
    roots += tuple((r.registry_namespace, r.registry_name) for r in requirements)
    replies, cache, active, visited = [], {}, set(), set()
    catalog_bytes = 0

    def fetch(kind, arguments):
        nonlocal catalog_bytes
        owner._checkpoint()
        key = kind, arguments
        if key in cache:
            return cache[key]
        if len(cache) >= MAX_OBJECTS * 16:
            raise ExecutionError("POSTGRES_SOURCE_RESOURCE_LIMIT")
        metadata, rows, native = owner._catalog_read(SQL[kind], arguments)
        del metadata
        catalog_bytes += len(repr(rows).encode())
        if catalog_bytes > min(MAX_CATALOG_BYTES, owner.request.limits.max_bytes):
            raise ExecutionError("POSTGRES_SOURCE_RESOURCE_LIMIT")
        reply = CatalogReply(kind, arguments, rows, native)
        replies.append(reply)
        cache[key] = rows
        return rows

    def one(kind, oid):
        rows = fetch(kind, (oid,))
        if len(rows) != 1:
            raise ExecutionError("POSTGRES_SOURCE_CATALOG_REQUIRED")
        return rows[0]

    def role(oid, depth=0):
        if depth > MAX_DEPTH:
            raise ExecutionError("POSTGRES_SOURCE_RESOURCE_LIMIT")
        if ("role", (oid,)) in cache:
            return
        if sum(k[0] == "role" for k in cache) >= MAX_OBJECTS:
            raise ExecutionError("POSTGRES_SOURCE_RESOURCE_LIMIT")
        one("role", oid)
        for member in fetch("members", (oid,)):
            role(member[0], depth + 1)

    def function(oid):
        one("function", oid)

    def typ(oid):
        if ("type", (oid,)) in cache:
            return
        row = one("type", oid)
        for function_oid in row[6:10]:
            if function_oid:
                function(function_oid)

    def expression(text, depth):
        tree = parse_native(text)
        for _path, node in nodes(tree):
            values = dict(node.fields)
            if node.tag == "RANGETBLENTRY" and values.get("rtekind") == 0:
                relation(values["relid"], depth + 1, values["inh"])
            if node.tag in (
                "OPEXPR",
                "DISTINCTEXPR",
                "NULLIFEXPR",
                "SCALARARRAYOPEXPR",
            ):
                op = one("operator", values["opno"])
                function(op[6])
            for key in ("funcid", "opfuncid"):
                if values.get(key):
                    function(values[key])
            for key in (
                "vartype",
                "consttype",
                "funcresulttype",
                "opresulttype",
                "resulttype",
                "type",
                "paramtype",
            ):
                if values.get(key):
                    typ(values[key])
            if node.tag == "SETOPERATIONSTMT":
                for oid in (values.get("colTypes") or ())[1:]:
                    typ(oid)
                for oid in (values.get("colCollations") or ())[1:]:
                    if oid:
                        one("collation", oid)
            for key in (
                "varcollid",
                "constcollid",
                "funccollid",
                "opcollid",
                "inputcollid",
                "resultcollid",
                "collOid",
            ):
                if values.get(key):
                    one("collation", values[key])
        return tree

    def relation(oid, depth=0, inherit=True):
        if oid in active or depth > MAX_DEPTH:
            raise ExecutionError("POSTGRES_SOURCE_CYCLE_OR_DEPTH")
        if (oid, inherit) in visited:
            return
        if sum(k[0] == "relation" for k in cache) >= MAX_OBJECTS:
            raise ExecutionError("POSTGRES_SOURCE_RESOURCE_LIMIT")
        active.add(oid)
        row = one("relation", oid)
        if row[1] not in owner.request.postgres_adbc_deployment.schemas:
            raise ExecutionError("POSTGRES_ADBC_DEPLOYMENT_PREMISE_SCOPE")
        role(row[5])
        if row[11]:
            function(row[11])
        for attribute in fetch("attributes", (oid,)):
            typ(attribute[2])
            if attribute[3]:
                one("collation", attribute[3])
            if attribute[5] is not None:
                expression(attribute[5], depth)
        children = fetch("children", (oid,))
        if inherit:
            for child in children:
                relation(child[0], depth + 1)
        for rule in fetch("rewrite", (oid,)):
            expression(rule[5], depth)
        active.remove(oid)
        visited.add((oid, inherit))

    role(owner.context[4])
    root_oids = []
    for root in roots:
        if root[0] not in owner.request.postgres_adbc_deployment.schemas:
            raise ExecutionError("POSTGRES_ADBC_DEPLOYMENT_PREMISE_SCOPE")
        found = fetch("resolve", root)
        if len(found) != 1 or len(found[0]) != 1:
            raise ExecutionError("POSTGRES_SOURCE_CATALOG_REQUIRED")
        root_oids.append(found[0][0])
        relation(found[0][0])
    accepted_replies = tuple(replies)
    paths = verify_catalog(
        roots,
        tuple(root_oids),
        accepted_replies,
        owner.context,
        owner.request.postgres_adbc_deployment.schemas,
        owner._context_native,
    )
    qualification = SourceQualification(
        owner,
        owner.request,
        owner.context,
        roots,
        accepted_replies,
        paths,
        (roots, reply_state(accepted_replies), paths),
    )
    owner._qualification = owner._owned_qualification = qualification
    qualification.verify(owner)
    return qualification


def reply_state(replies):
    return tuple(
        (
            r,
            r.kind,
            r.arguments,
            r.rows,
            r.native,
            r.native.sql,
            r.native.arguments,
            r.native.rows,
            r.native.terminal,
        )
        for r in replies
    )
