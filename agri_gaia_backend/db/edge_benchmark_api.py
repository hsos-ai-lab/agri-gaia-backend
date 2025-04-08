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

import datetime

from typing import List, Optional
from sqlalchemy.orm import Session
from agri_gaia_backend.db.models import BenchmarkJob
from agri_gaia_backend.schemas.edge_benchmark import BenchmarkJobRun


def get_all_benchmark_jobs(
    db: Session, skip: int = 0, limit: int = 100
) -> List[BenchmarkJob]:
    return db.query(BenchmarkJob).offset(skip).limit(limit).all()


def get_benchmark_job_by_id(db: Session, job_id: int) -> Optional[BenchmarkJob]:
    return db.query(BenchmarkJob).filter(BenchmarkJob.id == job_id).first()


def delete_benchmark_job(db: Session, benchmark_job: BenchmarkJob) -> bool:
    db.delete(benchmark_job)
    db.commit()
    return True


def create_benchmark_job(
    db: Session,
    owner: str,
    bucket_name: str,
    minio_location: str,
    timestamp: datetime.datetime,
    last_modified: datetime.datetime,
    run: BenchmarkJobRun,
) -> BenchmarkJob:
    db_benchmark_job = BenchmarkJob(
        owner=owner,
        bucket_name=bucket_name,
        minio_location=minio_location,
        timestamp=timestamp,
        last_modified=last_modified,
        dataset_id=run.dataset_id,
        model_id=run.model_id,
        cpu_only=run.benchmark_config.cpu_only,
        edge_device=run.benchmark_config.edge_device.host,
        inference_client=run.benchmark_config.inference_client.__class__.__name__,
    )
    db.add(db_benchmark_job)
    db.commit()
    db.refresh(db_benchmark_job)
    return db_benchmark_job
