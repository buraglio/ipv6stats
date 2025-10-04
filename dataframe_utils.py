"""
DataFrame optimization utilities
Reduces memory usage through efficient data types
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


def optimize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Optimize DataFrame memory usage by downcasting numeric types

    Args:
        df: DataFrame to optimize

    Returns:
        Optimized DataFrame with reduced memory footprint
    """
    start_mem = df.memory_usage(deep=True).sum() / 1024**2

    # Optimize integer columns
    for col in df.select_dtypes(include=['int64']).columns:
        df[col] = pd.to_numeric(df[col], downcast='integer')

    # Optimize float columns
    for col in df.select_dtypes(include=['float64']).columns:
        df[col] = pd.to_numeric(df[col], downcast='float')

    # Optimize object columns to category if cardinality is low
    for col in df.select_dtypes(include=['object']).columns:
        num_unique = df[col].nunique()
        num_total = len(df[col])
        if num_unique / num_total < 0.5:  # Less than 50% unique values
            df[col] = df[col].astype('category')

    end_mem = df.memory_usage(deep=True).sum() / 1024**2
    reduction = 100 * (start_mem - end_mem) / start_mem

    logger.info(f"DataFrame optimized: {start_mem:.2f}MB -> {end_mem:.2f}MB ({reduction:.1f}% reduction)")

    return df


def create_optimized_dataframe(data: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Create a memory-optimized DataFrame from data

    Args:
        data: List of dictionaries

    Returns:
        Optimized DataFrame
    """
    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)
    return optimize_dataframe(df)


def safe_dataframe_operation(df: pd.DataFrame, operation: callable, *args, **kwargs) -> pd.DataFrame:
    """
    Safely perform DataFrame operation with error handling

    Args:
        df: DataFrame to operate on
        operation: Function to apply
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Result DataFrame or original on error
    """
    try:
        result = operation(df, *args, **kwargs)
        return result
    except Exception as e:
        logger.error(f"DataFrame operation failed: {e}")
        return df


def reduce_dataframe_size(df: pd.DataFrame, max_rows: int = 1000) -> pd.DataFrame:
    """
    Reduce DataFrame size for display purposes

    Args:
        df: DataFrame to reduce
        max_rows: Maximum rows to keep

    Returns:
        Reduced DataFrame
    """
    if len(df) <= max_rows:
        return df

    # Keep most important rows (e.g., sorted by key column if exists)
    if 'rank' in df.columns:
        return df.nsmallest(max_rows, 'rank')
    elif 'ipv6_percentage' in df.columns:
        return df.nlargest(max_rows, 'ipv6_percentage')
    else:
        return df.head(max_rows)
