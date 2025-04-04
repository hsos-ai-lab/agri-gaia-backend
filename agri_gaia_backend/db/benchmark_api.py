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
from agri_gaia_backend.schemas.benchmark_job_metadata import BenchmarkJobMetadata


def get_benchmark_result(
    db: Session, benchmark_id: int
) -> Optional[models.BenchmarkJob]:
    return (
        db.query(models.BenchmarkJob)
        .filter(models.Benchmark.id == benchmark_id)
        .first()
    )


def get_benchmark_result_by_job_id(
    db: Session, job_id: int
) -> Optional[models.BenchmarkJob]:
    return (
        db.query(models.BenchmarkJob).filter(models.Benchmark.job_id == job_id).first()
    )


def get_benchmarks_by_owner(
    db: Session, owner: str, skip: int = 0, limit: int = 100
) -> List[models.BenchmarkJob]:
    return (
        db.query(models.BenchmarkJob)
        .filter(models.BenchmarkJob.owner == owner)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_benchmarks_by_dataset(
    db: Session, dataset_id: int, skip: int = 0, limit: int = 100
) -> List[models.BenchmarkJob]:
    return (
        db.query(models.BenchmarkJob)
        .filter(models.BenchmarkJob.dataset_id == dataset_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_benchmarks_by_device_ip(
    db: Session, device_ip: str, skip: int = 0, limit: int = 100
) -> List[models.BenchmarkJob]:
    return (
        db.query(models.BenchmarkJob)
        .filter(models.BenchmarkJob.device_ip == device_ip)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_benchmarks_by_device_name(
    db: Session, device_name: str, skip: int = 0, limit: int = 100
) -> List[models.BenchmarkJob]:
    return (
        db.query(models.BenchmarkJob)
        .filter(models.BenchmarkJob.device_name == device_name)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_benchmark_by_name(
    db: Session, name: str, skip: int = 0, limit: int = 1
) -> models.BenchmarkJob:
    return (
        db.query(models.BenchmarkJob)
        .filter(models.BenchmarkJob.name == name)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_benchmarks_by_metadata_uri(
    db: Session, skip: int = 0, limit: int = 100, uris: Array = []
) -> List[models.BenchmarkJob]:
    return (
        db.query(models.BenchmarkJob)
        .filter(models.BenchmarkJob.metadata_uri.in_(uris))
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_benchmarks(
    db: Session, skip: int = 0, limit: int = 100
) -> List[models.BenchmarkJob]:
    return db.query(models.BenchmarkJob).offset(skip).limit(limit).all()


def create_benchmark_job(
    db: Session,
    owner: str,
    bucket_name: str,
    minio_location: str,
    timestamp: datetime.datetime,
    last_modified: datetime.datetime,
    metadata: BenchmarkJobMetadata,
) -> models.BenchmarkJob:
    db_benchmark_job = models.BenchmarkJob(
        owner=owner,
        bucket_name=bucket_name,
        minio_location=minio_location,
        timestamp=timestamp,
        last_modified=last_modified,
        dataset_id=metadata.dataset_id,
        model_id=metadata.model_id,
        cpu_only=metadata.benchmark_config.cpu_only,
        edge_device=metadata.benchmark_config.edge_device.host,
        inference_client=metadata.benchmark_config.inference_client.__class__.__name__,
    )
    db.add(db_benchmark_job)
    db.commit()
    db.refresh(db_benchmark_job)
    return db_benchmark_job


def update_benchmark(
    db: Session, benchmark: models.BenchmarkJob
) -> models.BenchmarkJob:
    db.add(benchmark)
    db.commit()
    db.refresh(benchmark)
    return benchmark


def delete_benchmark(db: Session, benchmark: models.BenchmarkJob) -> bool:
    db.delete(benchmark)
    db.commit()
    return True
