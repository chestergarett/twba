import pandas as pd
import os
from pathlib import Path
from datetime import datetime, timedelta
import json

def normalize_device_id(device_id):
    """Normalize device ID to match SCOUTPI format"""
    if pd.isna(device_id):
        return None
    device_id = str(device_id).replace('.0', '')
    try:
        device_num = int(float(device_id))
        return f"SCOUTPI-{device_num:04d}"
    except:
        return None

def parse_json_value(value):
    """Safely parse JSON-like values into Python objects."""
    if pd.isna(value):
        return {}
    if isinstance(value, (dict, list)):
        return value
    try:
        value_str = str(value).strip()
        if value_str.startswith('{') and value_str.endswith('}'):
            return json.loads(value_str)
        if value_str.startswith('[') and value_str.endswith(']'):
            return json.loads(value_str)
    except Exception:
        pass
    return {}

def expand_privacy_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Expand nested privacy JSON into individual columns prefixed with privacy_.
    """
    return expand_json_column(df, 'privacy', 'privacy_')

def expand_json_column(df: pd.DataFrame, column_name: str, prefix: str) -> pd.DataFrame:
    """Expand a JSON/dict column into multiple prefixed columns."""
    if column_name not in df.columns:
        return df
    
    parsed_series = df[column_name].apply(parse_json_value)
    if parsed_series.empty:
        return df
    
    expanded = pd.json_normalize(parsed_series).add_prefix(prefix)
    
    for col in expanded.columns:
        if col not in df.columns or df[col].isna().all():
            df[col] = expanded[col]
        else:
            df[col] = df[col].combine_first(expanded[col])
    
    return df

def test_matching_strategies(video_df: pd.DataFrame, voice_df: pd.DataFrame) -> dict:
    """
    Test different matching strategies and return results.
    
    Returns:
        Dictionary with match counts for each strategy
    """
    results = {}
    
    # Strategy 1: Direct match InteractionID = transactionId
    video_ids = set(video_df['InteractionID'].dropna().astype(str).str.lower().str.strip())
    voice_ids = set(voice_df['transactionId'].dropna().astype(str).str.lower().str.strip())
    direct_matches = video_ids & voice_ids
    results['direct_match'] = {
        'count': len(direct_matches),
        'percentage': len(direct_matches) / len(voice_ids) * 100 if len(voice_ids) > 0 else 0,
        'key': 'InteractionID = transactionId'
    }
    
    # Strategy 2: Normalized canonical_tx_id
    video_df['canonical_clean'] = video_df['canonical_tx_id'].astype(str).str.lower().str.strip().str.replace('-', '').str.replace(' ', '')
    voice_df['tx_normalized'] = voice_df['transactionId'].astype(str).str.lower().str.replace('-', '').str.replace(' ', '')
    video_canonical = set(video_df['canonical_clean'].dropna())
    voice_normalized = set(voice_df['tx_normalized'].dropna())
    canonical_matches = video_canonical & voice_normalized
    results['canonical_match'] = {
        'count': len(canonical_matches),
        'percentage': len(canonical_matches) / len(voice_ids) * 100 if len(voice_ids) > 0 else 0,
        'key': 'canonical_tx_id (normalized) = transactionId (normalized)'
    }
    
    # Strategy 3: Composite key - StoreID + DeviceID + Date proximity
    # Normalize StoreID
    video_df['StoreID_str'] = video_df['StoreID'].astype(str).str.replace('.0', '').str.strip()
    voice_df['storeId_str'] = voice_df['storeId'].astype(str).str.strip()
    
    # Normalize DeviceID
    video_df['DeviceID_normalized'] = video_df['DeviceID'].apply(normalize_device_id)
    
    # Convert TransactionDate to datetime
    video_df['TransactionDate_dt'] = pd.to_datetime(video_df['TransactionDate'], errors='coerce')
    
    # Extract consentTimestamp from voice (it's in transactionContext JSON)
    def extract_consent_timestamp(row):
        try:
            if pd.notna(row.get('privacy')):
                privacy_str = str(row['privacy'])
                if privacy_str.startswith('{'):
                    privacy_dict = json.loads(privacy_str)
                    consent_ts = privacy_dict.get('consentTimestamp', '')
                    if consent_ts:
                        # Parse ISO format timestamp
                        try:
                            return pd.to_datetime(consent_ts.split('.')[0], errors='coerce')
                        except:
                            return None
        except:
            pass
        return None
    
    voice_df['consentTimestamp_dt'] = voice_df.apply(extract_consent_timestamp, axis=1)
    
    # Try matching on StoreID + DeviceID + Date (within 1 hour)
    composite_matches = 0
    matched_pairs = []
    
    for idx, voice_row in voice_df.iterrows():
        if pd.isna(voice_row['storeId_str']) or pd.isna(voice_row['deviceId']):
            continue
        
        # Find matching video rows
        video_matches = video_df[
            (video_df['StoreID_str'] == voice_row['storeId_str']) &
            (video_df['DeviceID_normalized'] == voice_row['deviceId'])
        ]
        
        if len(video_matches) > 0:
            # If we have timestamps, try to match within 1 hour
            if pd.notna(voice_row['consentTimestamp_dt']):
                video_matches = video_matches[
                    (video_matches['TransactionDate_dt'].notna()) &
                    (abs(video_matches['TransactionDate_dt'] - voice_row['consentTimestamp_dt']) <= timedelta(hours=1))
                ]
            
            if len(video_matches) > 0:
                # If still multiple matches, prefer exact transactionId match
                exact_match = video_matches[video_matches['InteractionID'].str.lower().str.strip() == voice_row['transactionId'].lower().strip()]
                if len(exact_match) > 0:
                    composite_matches += 1
                    matched_pairs.append((voice_row['transactionId'], exact_match.iloc[0]['InteractionID']))
                elif len(video_matches) == 1:
                    # Single match within time window
                    composite_matches += 1
                    matched_pairs.append((voice_row['transactionId'], video_matches.iloc[0]['InteractionID']))
    
    results['composite_match'] = {
        'count': composite_matches,
        'percentage': composite_matches / len(voice_df) * 100 if len(voice_df) > 0 else 0,
        'key': 'StoreID + DeviceID + Date proximity (1 hour)'
    }
    
    # Strategy 4: Transcription text similarity (for records without exact ID match)
    # This would require fuzzy matching library, so we'll just note it as a potential strategy
    results['text_similarity_note'] = {
        'count': 0,
        'percentage': 0,
        'key': 'TranscriptionText ≈ audioTranscript (requires fuzzy matching)',
        'note': 'Could match remaining records using text similarity between TranscriptionText and audioTranscript'
    }
    
    return results

def perform_data_quality_check(video_df: pd.DataFrame, voice_df: pd.DataFrame, 
                                video_key: str, voice_key: str) -> dict:
    """
    Perform data quality checks to find unmatched transactionIds.
    
    Args:
        video_df: DataFrame from VideoTable.csv
        voice_df: DataFrame from voice_inputs_combined.csv
        video_key: Column name in video_df to use for matching
        voice_key: Column name in voice_df to use for matching
        
    Returns:
        Dictionary with data quality metrics
    """
    # Get unique transactionIds from both dataframes
    video_ids = set(video_df[video_key].dropna().astype(str).str.lower().str.strip())
    voice_ids = set(voice_df[voice_key].dropna().astype(str).str.lower().str.strip())
    
    # Find unmatched IDs
    voice_only = voice_ids - video_ids
    video_only = video_ids - voice_ids
    matched = voice_ids & video_ids
    
    # Create results dictionary
    quality_report = {
        'total_voice_transactions': len(voice_ids),
        'total_video_transactions': len(video_ids),
        'matched_transactions': len(matched),
        'voice_only_transactions': len(voice_only),
        'video_only_transactions': len(video_only),
        'match_rate': len(matched) / len(voice_ids) * 100 if len(voice_ids) > 0 else 0,
        'voice_only_list': sorted(list(voice_only)),
        'video_only_list': sorted(list(video_only))
    }
    
    return quality_report

def merge_voice_video_data(video_path: str, voice_path: str, output_dir: str, 
                           matching_strategy: str = 'direct'):
    """
    Perform full join (outer join) between VideoTable.csv and voice_inputs_combined.csv
    on transactionId, add _voice suffix to voice columns, and perform data quality checks.
    
    Args:
        video_path: Path to VideoTable.csv
        voice_path: Path to voice_inputs_combined.csv
        output_dir: Directory to save output files
        matching_strategy: 'direct' (InteractionID=transactionId), 'canonical' (normalized), 
                          or 'composite' (StoreID+DeviceID+Date)
    """
    print("Loading data files...")
    
    # Load dataframes
    video_df = pd.read_csv(video_path, low_memory=False)
    voice_df = pd.read_csv(voice_path)
    voice_df = expand_privacy_columns(voice_df)
    voice_df = expand_json_column(voice_df, 'totals', 'totals_')
    voice_df = expand_json_column(voice_df, 'transactionContext', 'transactionContext_')
    
    print(f"Video table shape: {video_df.shape}")
    print(f"Voice table shape: {voice_df.shape}")
    
    # Test different matching strategies
    print("\n" + "="*60)
    print("TESTING MATCHING STRATEGIES")
    print("="*60)
    strategy_results = test_matching_strategies(video_df.copy(), voice_df.copy())
    
    for strategy_name, result in strategy_results.items():
        if 'note' not in result:
            print(f"\n{strategy_name.replace('_', ' ').title()}:")
            print(f"  Key: {result['key']}")
            print(f"  Matches: {result['count']:,} ({result['percentage']:.2f}% of voice records)")
        else:
            print(f"\n{strategy_name.replace('_', ' ').title()}:")
            print(f"  {result['key']}")
            print(f"  Note: {result.get('note', '')}")
    
    # Determine best strategy
    best_strategy = max(
        [(k, v) for k, v in strategy_results.items() if 'percentage' in v and 'note' not in v],
        key=lambda x: x[1]['percentage']
    )
    print(f"\n{'='*60}")
    print(f"BEST MATCHING STRATEGY: {best_strategy[0].replace('_', ' ').title()}")
    print(f"  Match Rate: {best_strategy[1]['percentage']:.2f}%")
    print(f"  Key Used: {best_strategy[1]['key']}")
    print(f"{'='*60}\n")
    
    # Use the specified matching strategy
    if matching_strategy == 'canonical':
        video_key = 'canonical_tx_id'
        voice_key = 'transactionId'
        # Normalize for matching
        video_df['canonical_clean'] = video_df['canonical_tx_id'].astype(str).str.lower().str.strip().str.replace('-', '').str.replace(' ', '')
        voice_df['tx_normalized'] = voice_df['transactionId'].astype(str).str.lower().str.replace('-', '').str.replace(' ', '')
        video_df = video_df.rename(columns={'canonical_clean': 'match_key'})
        voice_df = voice_df.rename(columns={'tx_normalized': 'match_key'})
        join_key = 'match_key'
    else:  # default to direct
        video_key = 'InteractionID'
        voice_key = 'transactionId'
        # Normalize for matching
        video_df['match_key'] = video_df[video_key].astype(str).str.lower().str.strip()
        voice_df['match_key'] = voice_df[voice_key].astype(str).str.lower().str.strip()
        join_key = 'match_key'
    
    print(f"Using matching strategy: {matching_strategy}")
    print(f"Join key: {join_key}")
    
    # Add _voice suffix to all voice columns except the join key
    voice_columns_rename = {col: f"{col}_voice" for col in voice_df.columns if col not in [voice_key, 'match_key']}
    voice_df_renamed = voice_df.rename(columns=voice_columns_rename)
    
    # Perform full join (outer join - keeping all records from both dataframes)
    print("\nPerforming full join (outer join)...")
    merged_df = video_df.merge(
        voice_df_renamed,
        on=join_key,
        how='outer',
        suffixes=('', '_voice_dup')
    )
    
    # Remove any duplicate suffix columns and the temporary match_key
    merged_df = merged_df.loc[:, ~merged_df.columns.str.endswith('_voice_dup')]
    if 'match_key' in merged_df.columns:
        merged_df = merged_df.drop(columns=['match_key'])
    
    print(f"Merged dataframe shape: {merged_df.shape}")
    
    # Perform data quality checks
    print("\nPerforming data quality checks...")
    quality_report = perform_data_quality_check(
        video_df, 
        voice_df, 
        video_key, 
        voice_key
    )
    
    # Print quality report
    print("\n" + "="*60)
    print("DATA QUALITY REPORT")
    print("="*60)
    print(f"Total voice transactions: {quality_report['total_voice_transactions']:,}")
    print(f"Total video transactions: {quality_report['total_video_transactions']:,}")
    print(f"Matched transactions: {quality_report['matched_transactions']:,}")
    print(f"Match rate: {quality_report['match_rate']:.2f}%")
    print(f"\nVoice-only transactions (no match in video): {quality_report['voice_only_transactions']:,}")
    print(f"Video-only transactions (no match in voice): {quality_report['video_only_transactions']:,}")
    print("="*60)
    
    # Save outputs
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # Save merged dataframe
    merged_csv_path = output_dir / "voice_video_merged.csv"
    merged_excel_path = output_dir / "voice_video_merged.xlsx"
    
    print(f"\nSaving merged dataframe to CSV...")
    merged_df.to_csv(merged_csv_path, index=False, encoding='utf-8')
    print(f"  Saved: {merged_csv_path}")
    
    try:
        print(f"\nSaving merged dataframe to Excel...")
        merged_df.to_excel(merged_excel_path, index=False, engine='openpyxl')
        print(f"  Saved: {merged_excel_path}")
    except ImportError:
        print("  openpyxl not installed. Skipping Excel export. Install with: pip install openpyxl")
    
    # Save matching strategy analysis
    strategy_path = output_dir / "matching_strategy_analysis.txt"
    with open(strategy_path, 'w', encoding='utf-8') as f:
        f.write("MATCHING STRATEGY ANALYSIS\n")
        f.write("="*60 + "\n\n")
        for strategy_name, result in strategy_results.items():
            if 'note' not in result:
                f.write(f"{strategy_name.replace('_', ' ').title()}:\n")
                f.write(f"  Key: {result['key']}\n")
                f.write(f"  Matches: {result['count']:,} ({result['percentage']:.2f}% of voice records)\n\n")
            else:
                f.write(f"{strategy_name.replace('_', ' ').title()}:\n")
                f.write(f"  {result['key']}\n")
                f.write(f"  Note: {result.get('note', '')}\n\n")
        f.write(f"\nBEST STRATEGY: {best_strategy[0].replace('_', ' ').title()}\n")
        f.write(f"  Match Rate: {best_strategy[1]['percentage']:.2f}%\n")
        f.write(f"  Key Used: {best_strategy[1]['key']}\n")
    
    print(f"  Saved: {strategy_path}")
    
    # Save data quality report
    quality_report_path = output_dir / "data_quality_report.txt"
    with open(quality_report_path, 'w', encoding='utf-8') as f:
        f.write("DATA QUALITY REPORT\n")
        f.write("="*60 + "\n\n")
        f.write(f"Total voice transactions: {quality_report['total_voice_transactions']:,}\n")
        f.write(f"Total video transactions: {quality_report['total_video_transactions']:,}\n")
        f.write(f"Matched transactions: {quality_report['matched_transactions']:,}\n")
        f.write(f"Match rate: {quality_report['match_rate']:.2f}%\n\n")
        f.write(f"Voice-only transactions (no match in video): {quality_report['voice_only_transactions']:,}\n")
        f.write(f"Video-only transactions (no match in voice): {quality_report['video_only_transactions']:,}\n\n")
        
        if quality_report['voice_only_list']:
            f.write(f"\nVoice-only transaction IDs ({len(quality_report['voice_only_list'])}):\n")
            f.write("-"*60 + "\n")
            for tx_id in quality_report['voice_only_list'][:100]:  # Limit to first 100
                f.write(f"{tx_id}\n")
            if len(quality_report['voice_only_list']) > 100:
                f.write(f"... and {len(quality_report['voice_only_list']) - 100} more\n")
        
        if quality_report['video_only_list']:
            f.write(f"\nVideo-only transaction IDs ({len(quality_report['video_only_list'])}):\n")
            f.write("-"*60 + "\n")
            for tx_id in quality_report['video_only_list'][:100]:  # Limit to first 100
                f.write(f"{tx_id}\n")
            if len(quality_report['video_only_list']) > 100:
                f.write(f"... and {len(quality_report['video_only_list']) - 100} more\n")
    
    print(f"  Saved: {quality_report_path}")
    
    # Save unmatched transaction IDs to separate CSV files
    if quality_report['voice_only_list']:
        voice_only_df = voice_df[voice_df[voice_key].astype(str).str.lower().str.strip().isin(quality_report['voice_only_list'])]
        voice_only_path = output_dir / "voice_only_transactions.csv"
        voice_only_df.to_csv(voice_only_path, index=False, encoding='utf-8')
        print(f"  Saved voice-only transactions: {voice_only_path}")
    
    if quality_report['video_only_list']:
        video_only_df = video_df[video_df[video_key].astype(str).str.lower().str.strip().isin(quality_report['video_only_list'])]
        video_only_path = output_dir / "video_only_transactions.csv"
        video_only_df.to_csv(video_only_path, index=False, encoding='utf-8')
        print(f"  Saved video-only transactions: {video_only_path}")
    
    print("\nMerge and data quality check complete!")
    return merged_df, quality_report, strategy_results

def main():
    # Set paths
    base_dir = Path(__file__).parent.parent
    video_path = base_dir / "video_inputs" / "VideoTable.csv"
    voice_path = base_dir / "output" / "voice_inputs_combined.csv"
    output_dir = base_dir / "output"
    
    # Check if input files exist
    if not video_path.exists():
        raise FileNotFoundError(f"VideoTable.csv not found at {video_path}")
    if not voice_path.exists():
        raise FileNotFoundError(f"voice_inputs_combined.csv not found at {voice_path}")
    
    # Perform merge and data quality checks
    # Options: 'direct' (default), 'canonical', or 'composite'
    merged_df, quality_report, strategy_results = merge_voice_video_data(
        str(video_path),
        str(voice_path),
        str(output_dir),
        matching_strategy='direct'  # Change to 'canonical' if that works better
    )
    
    return merged_df, quality_report, strategy_results

if __name__ == "__main__":
    main()
