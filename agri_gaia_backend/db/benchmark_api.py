# SPDX-FileCopyrightText: 2024 Osnabrück University of Applied Sciences
# SPDX-FileContributor: Andreas Schliebitz
# SPDX-FileContributor: Henri Graf
# SPDX-FileContributor: Jonas Tüpker
# SPDX-FileContributor: Lukas Hesse
# SPDX-FileContributor: Maik Fruhner
# SPDX-FileContributor: Prof. Dr.-Ing. Heiko Tapken
# SPDX-FileContributor: Tobias Wamhof
#
# SPDX-License-Identifier: MIT

from multiprocessing.dummy import Array
from typing import List, Optional
from sqlalchemy.orm import Session
import datetime

from agri_gaia_backend.db import models


def get_benchmark_result(db: Session, benchmark_id: int) -> Optional[models.Benchmark]:
    return (
        db.query(models.Benchmark).filter(models.Benchmark.id == benchmark_id).first()
    )


def get_benchmark_result_by_job_id(
    db: Session, job_id: int
) -> Optional[models.Benchmark]:
    return db.query(models.Benchmark).filter(models.Benchmark.job_id == job_id).first()


def get_benchmarks_by_owner(
    db: Session, owner: str, skip: int = 0, limit: int = 100
) -> List[models.Benchmark]:
    return (
        db.query(models.Benchmark)
        .filter(models.Benchmark.owner == owner)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_benchmarks_by_dataset(
    db: Session, dataset_id: int, skip: int = 0, limit: int = 100
) -> List[models.Benchmark]:
    return (
        db.query(models.Benchmark)
        .filter(models.Benchmark.dataset_id == dataset_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_benchmarks_by_device_ip(
    db: Session, device_ip: str, skip: int = 0, limit: int = 100
) -> List[models.Benchmark]:
    return (
        db.query(models.Benchmark)
        .filter(models.Benchmark.device_ip == device_ip)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_benchmarks_by_device_name(
    db: Session, device_name: str, skip: int = 0, limit: int = 100
) -> List[models.Benchmark]:
    return (
        db.query(models.Benchmark)
        .filter(models.Benchmark.device_name == device_name)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_benchmark_by_name(
    db: Session, name: str, skip: int = 0, limit: int = 1
) -> models.Benchmark:
    return (
        db.query(models.Benchmark)
        .filter(models.Benchmark.name == name)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_benchmarks_by_metadata_uri(
    db: Session, skip: int = 0, limit: int = 100, uris: Array = []
) -> List[models.Benchmark]:
    return (
        db.query(models.Benchmark)
        .filter(models.Benchmark.metadata_uri.in_(uris))
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_benchmarks(
    db: Session, skip: int = 0, limit: int = 100
) -> List[models.Benchmark]:
    return db.query(models.Benchmark).offset(skip).limit(limit).all()


def create_benchmark(
    db: Session,
    name: str,
    owner: str,
    last_modified: datetime.datetime,
    bucket_name: str,
    minio_location: str,
    timestamp: datetime.datetime,
    dataset_id=int,
    job_id=str,
    device_ip=str,
    device_name=str,
) -> models.Benchmark:
    db_benchmark = models.Benchmark(
        name=name,
        owner=owner,
        last_modified=last_modified,
        bucket_name=bucket_name,
        minio_location=minio_location,
        timestamp=timestamp,
        dataset_id=dataset_id,
        job_id=job_id,
        device_ip=device_ip,
        device_name=device_name,
    )
    db.add(db_benchmark)
    db.commit()
    db.refresh(db_benchmark)
    return db_benchmark


def update_benchmark(db: Session, benchmark: models.Benchmark) -> models.Benchmark:
    db.add(benchmark)
    db.commit()
    db.refresh(benchmark)
    return benchmark


def delete_benchmark(db: Session, benchmark: models.Benchmark) -> bool:
    db.delete(benchmark)
    db.commit()
    return True
