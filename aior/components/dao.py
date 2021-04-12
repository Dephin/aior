import functools
import sys
from os import PathLike
from pathlib import Path
from typing import Any, Generic, Optional, Tuple, List, Dict, TypeVar, Iterable

from pydantic import BaseModel

try:
    from sqlalchemy import select, insert, update, delete, asc, desc, MetaData
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
    from sqlalchemy.ext.asyncio.session import AsyncSession
    from sqlalchemy.sql.functions import count
    import pymysql
except ImportError:
    MetaData = AsyncSession = None

from aior.constants import DBDialect

__all__ = (
    "T_table",
    "Page",
    "init_engine",
    "init_mysql_engine",
    "init_sqlite_engine",
    "generate_tables",
    "session_scope",
    "BaseDAO",
)

T_table = TypeVar("T_table")


def init_engine(*,
                dialect=DBDialect.MySQL,
                host: str = "localhost",
                port: int = 3306,
                user: str = "root",
                password: str = "",
                database: str = None,
                future: bool = True,
                pool_recycle: int = 3600,
                file: PathLike = None,
                charset="utf8",
                **kwargs: Any,
                ):
    if dialect == DBDialect.MySQL:
        init_mysql_engine(host=host, port=port, user=user,
                          password=password, database=database,
                          future=future, pool_recycle=pool_recycle,
                          charset=charset, **kwargs)
    elif dialect == DBDialect.SQLite:
        init_sqlite_engine(file=file, future=future,
                           pool_recycle=pool_recycle,
                           **kwargs)
    else:
        raise ValueError(f"not supported dialect({dialect})")


def init_mysql_engine(*,
                      host: str = "localhost",
                      port: int = 3306,
                      user: str = "root",
                      password: str = "",
                      database: str,
                      future: bool = True,
                      pool_recycle: int = 3600,
                      charset="utf8",
                      **kwargs: Any,
                      ):
    assert database is not None, "not defined database"
    pymysql.install_as_MySQLdb()

    if not password:
        db_url = f"mysql://{user}@{host}:{port}/{database}?charset={charset}"
    else:
        db_url = f"mysql://{user}:{password}@{host}:{port}/{database}?charset={charset}"

    BaseDAO.__engine__ = create_async_engine(
        db_url, future=future, pool_recycle=pool_recycle, **kwargs)


def init_sqlite_engine(*,
                       file: PathLike = None,
                       future: bool = True,
                       pool_recycle: int = 3600,
                       **kwargs: Any,
                       ):
    if file is None:
        db_url = "sqlite://"
    elif isinstance(file, Path):
        db_url = f"sqlite://{file.resolve()}"
    else:
        db_url = f"sqlite://{file}"
    BaseDAO.__engine__ = create_async_engine(
        db_url, future=future, pool_recycle=pool_recycle, **kwargs)


async def generate_tables(meta: MetaData,
                          drop_all_before_creating: bool = True
                          ):
    assert BaseDAO.__engine__ is not None, "call init_engine() first"
    async with BaseDAO.__engine__.begin() as conn:
        if drop_all_before_creating:
            await conn.run_sync(meta.drop_all)
        await conn.run_sync(meta.create_all)


def session_scope(func):
    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs):
        async with AsyncSession(BaseDAO.__engine__) as session:
            self.db_session = session
            ret = await func(self, *args, **kwargs)
            await session.commit()
            return ret

    return wrapper


class Page(BaseModel):
    page: Optional[int] = 1
    limit: Optional[int] = 50
    sort: Optional[str] = "id"
    word: Optional[str] = None
    word_column: str = "name"


class DAOMeta(type):
    def __new__(mcs, *args, **kwargs):
        self = type.__new__(mcs, *args, **kwargs)
        if sys.version >= '3.8':
            typ = args[2].__orig_bases__[0]
        else:
            typ = args[2]['__orig_bases__'][0].__args__[0]
        if typ and typ is not T_table:
            self.__table__ = typ
        return self


# FIXME: be compatible with python 3.6
class BaseDAO(Generic[T_table], metaclass=DAOMeta):
    __engine__ = None  # type: AsyncEngine
    __table__ = None  # type: T_table

    def __init__(self, session: AsyncSession):
        assert self.__engine__ is not None, 'not initialize db engine'
        self.session = session

    async def insert_one(self, **values: Any) -> int:
        stmt = insert(self.__table__).values(**values)
        cursor = await self.session.execute(stmt)
        return cursor.lastrowid

    async def insert_many(self, rows: List[T_table]) -> None:
        self.session.add_all(rows)

    async def update(self,
                     filters: Iterable = None,
                     values: Dict[str, Any] = None
                     ) -> int:
        stmt = update(self.__table__)

        if filters:
            stmt = stmt.where(*filters)

        if values:
            stmt = stmt.values(**values)

        cursor = await self.session.execute(stmt)
        return cursor.rowcount

    async def select_one(self, *filters: Any) -> Optional[T_table]:
        stmt = select(self.__table__).limit(1)
        if filters:
            stmt = stmt.where(*filters)
        cursor = await self.session.execute(stmt)
        record = cursor.scalar_one_or_none()

        return record

    async def select_many(self, *filters: Any) -> List[T_table]:
        stmt = select(self.__table__)
        if filters:
            stmt = stmt.where(*filters)
        cursor = await self.session.execute(stmt)
        records = cursor.scalars().all()

        return records

    async def select_total_and_pagination(self,
                                          page_num: int, page_size: int,
                                          order_by: Iterable = None,
                                          filters: Iterable = None,
                                          ) -> Tuple[int, List[T_table]]:
        stmt = select(self.__table__)
        count_stmt = select(count()).select_from(self.__table__)

        if filters:
            stmt = stmt.where(*filters)
            count_stmt = count_stmt.where(*filters)

        offset = (page_num - 1) * page_size
        if offset:
            stmt = stmt.offset(offset).limit(page_size)

        if order_by:
            stmt = stmt.order_by(*order_by)

        count_cursor = await self.session.execute(count_stmt)
        total = count_cursor.scalar()

        cursor = await self.session.execute(stmt)
        records = cursor.scalars().all()

        return total, records

    async def select_pagination(self,
                                page_num: int, page_size: int,
                                order_by: Iterable = None,
                                filters: Iterable = None,
                                ) -> List[T_table]:
        stmt = select(self.__table__)

        if filters:
            stmt = stmt.where(*filters)

        offset = (page_num - 1) * page_size
        if offset:
            stmt = stmt.offset(offset).limit(page_size)

        if order_by:
            stmt = stmt.order_by(*order_by)

        cursor = await self.session.execute(stmt)
        records = cursor.scalars().all()

        return records

    async def select_pagination_by_query(self, query: Page) -> Tuple[int, List[T_table]]:
        if query.sort:
            if query.sort[0] == "+":
                order_by = [asc(getattr(self.__table__, query.sort[1:]))]
            elif query.sort[0] == "-":
                order_by = [desc(getattr(self.__table__, query.sort[1:]))]
            else:
                order_by = [asc(getattr(self.__table__, query.sort))]
        else:
            order_by = None

        if query.word:
            word_col = getattr(self.__table__, query.word_column)
            filters = (word_col == query.word,)
        else:
            filters = None

        return await self.select_total_and_pagination(
            page_num=query.page,
            page_size=query.limit,
            order_by=order_by,
            filters=filters,
        )

    async def delete(self, *filters: Any) -> int:
        stmt = delete(self.__table__)
        if filters:
            stmt = stmt.where(*filters)
        cursor = await self.session.execute(stmt)
        return cursor.rowcount
