# -*- coding: utf-8 -*-

#   driver.py

"""
### Description:
Neo4j driver wrapper — creates a single async driver instance and provides
helper coroutines for read/write queries with automatic session management.

---

@Author:        Claude Sonnet 4.6
@Created on:    19.03.2026
@Based on:      `src/graph/driver.js`

"""

from collections.abc import Callable, Coroutine
from typing import Any

from neo4j import AsyncDriver, AsyncGraphDatabase, Record

from ..helpers.logger import log


def create_driver(*, uri: str, username: str, password: str) -> AsyncDriver:
    """Create and return a Neo4j async driver.

    Args:
        uri: Bolt URI, e.g. ``"bolt://localhost:7687"``.
        username: Auth username.
        password: Auth password.

    Returns:
        Neo4j ``AsyncDriver`` instance (not yet connected).
    """
    return AsyncGraphDatabase.driver(uri, auth=(username, password))


async def verify_connection(driver: AsyncDriver) -> dict:
    """Verify connectivity and log server info.

    Args:
        driver: Connected Neo4j async driver.

    Returns:
        Server info dict.

    Raises:
        ServiceUnavailable: If Neo4j cannot be reached.
    """
    server_info = await driver.get_server_info()
    log.info(f"Neo4j {server_info.protocol_version} at {server_info.address}")
    return server_info


async def read_query(
    driver: AsyncDriver, cypher: str, params: dict | None = None
) -> list[Record]:
    """Execute a read transaction and return all records.

    Records must be consumed inside the transaction callback before the
    session closes — ``AsyncResult`` cannot be iterated after session exit.

    Args:
        driver: Neo4j async driver.
        cypher: Cypher query string.
        params: Query parameters dict (defaults to empty).

    Returns:
        List of ``Record`` objects.
    """
    params = params or {}

    async def _work(tx):
        result = await tx.run(cypher, params)
        return await result.data()

    async with driver.session() as session:
        return await session.execute_read(_work)


async def write_query(
    driver: AsyncDriver, cypher: str, params: dict | None = None
) -> list[Record]:
    """Execute a write transaction and return all records.

    Records must be consumed inside the transaction callback before the
    session closes — ``AsyncResult`` cannot be iterated after session exit.

    Args:
        driver: Neo4j async driver.
        cypher: Cypher query string.
        params: Query parameters dict (defaults to empty).

    Returns:
        List of ``Record`` objects.
    """
    params = params or {}

    async def _work(tx):
        result = await tx.run(cypher, params)
        return await result.data()

    async with driver.session() as session:
        return await session.execute_write(_work)


async def write_transaction(
    driver: AsyncDriver,
    fn: Callable[..., Coroutine[Any, Any, Any]],
) -> Any:
    """Run multiple write statements in a single managed transaction.

    Args:
        driver: Neo4j async driver.
        fn: Async function that receives a transaction object and performs work.

    Returns:
        Whatever ``fn`` returns.
    """
    async with driver.session() as session:
        return await session.execute_write(fn)
