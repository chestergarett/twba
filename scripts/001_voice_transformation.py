import json
import pandas as pd
import os
from pathlib import Path
from typing import Dict, Any

def load_json_files(base_path: str) -> pd.DataFrame:
    """
    Recursively load all JSON files from voice_inputs folder and combine into a dataframe.
    Preserves nested objects and arrays as JSON strings.
    
    Args:
        base_path: Path to the voice_inputs folder
        
    Returns:
        DataFrame with columns as JSON keys
    """
    json_files = []
    base_path = Path(base_path)
    
    # Recursively find all JSON files
    for json_file in base_path.rglob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Add file path for reference
                data['_file_path'] = str(json_file.relative_to(base_path))
                json_files.append(data)
        except Exception as e:
            print(f"Error reading {json_file}: {e}")
            continue
    
    if not json_files:
        print("No JSON files found!")
        return pd.DataFrame()
    
    # Convert to DataFrame
    # This will automatically create columns from the keys
    df = pd.DataFrame(json_files)
    
    # Convert nested objects and arrays to JSON strings for better CSV compatibility
    # This preserves the structure while making it exportable
    for col in df.columns:
        if col == '_file_path':
            continue
        # Check if column contains dict or list types
        if df[col].dtype == 'object':
            # Convert dict/list to JSON string, keep other types as-is
            df[col] = df[col].apply(
                lambda x: json.dumps(x, ensure_ascii=False) 
                if isinstance(x, (dict, list)) 
                else x
            )
    
    return df

def export_dataframe(df: pd.DataFrame, output_path: str, format: str = 'csv'):
    """
    Export dataframe to specified format.
    
    Args:
        df: DataFrame to export
        output_path: Output file path
        format: Export format ('csv', 'excel', 'parquet', 'json')
    """
    if df.empty:
        print("DataFrame is empty. Nothing to export.")
        return
    
    output_path = Path(output_path)
    
    if format.lower() == 'csv':
        df.to_csv(output_path, index=False, encoding='utf-8')
        print(f"Exported {len(df)} rows to {output_path}")
    
    elif format.lower() == 'excel':
        df.to_excel(output_path, index=False, engine='openpyxl')
        print(f"Exported {len(df)} rows to {output_path}")
    
    elif format.lower() == 'parquet':
        df.to_parquet(output_path, index=False)
        print(f"Exported {len(df)} rows to {output_path}")
    
    elif format.lower() == 'json':
        # Export as JSON lines (one JSON object per line)
        with open(output_path, 'w', encoding='utf-8') as f:
            for _, row in df.iterrows():
                row_dict = row.to_dict()
                # Parse JSON strings back to objects for cleaner JSON export
                for key, value in row_dict.items():
                    if isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
                        try:
                            row_dict[key] = json.loads(value)
                        except:
                            pass
                f.write(json.dumps(row_dict, ensure_ascii=False) + '\n')
        print(f"Exported {len(df)} rows to {output_path}")
    
    else:
        print(f"Unsupported format: {format}. Supported formats: csv, excel, parquet, json")

def main():
    # Set paths
    base_dir = Path(__file__).parent.parent
    voice_inputs_path = base_dir / "voice_inputs"
    output_dir = base_dir / "output"
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(exist_ok=True)
    
    print(f"Loading JSON files from {voice_inputs_path}...")
    
    # Load all JSON files into dataframe
    df = load_json_files(str(voice_inputs_path))
    
    if df.empty:
        print("No data to process.")
        return
    
    print(f"Loaded {len(df)} JSON files")
    print(f"DataFrame shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    
    # Export to multiple formats
    print("\nExporting dataframes...")
    
    # CSV export (nested structures as JSON strings)
    csv_path = output_dir / "voice_inputs_combined.csv"
    export_dataframe(df, str(csv_path), format='csv')
    
    # Excel export (nested structures as JSON strings)
    excel_path = output_dir / "voice_inputs_combined.xlsx"
    try:
        export_dataframe(df, str(excel_path), format='excel')
    except ImportError:
        print("openpyxl not installed. Skipping Excel export. Install with: pip install openpyxl")
    
    # Parquet export (better for preserving data types)
    parquet_path = output_dir / "voice_inputs_combined.parquet"
    try:
        export_dataframe(df, str(parquet_path), format='parquet')
    except ImportError:
        print("pyarrow not installed. Skipping Parquet export. Install with: pip install pyarrow")
    
    # JSON Lines export
    json_path = output_dir / "voice_inputs_combined.jsonl"
    export_dataframe(df, str(json_path), format='json')
    
    print("\nExport complete!")
    print(f"Output files saved to: {output_dir}")

if __name__ == "__main__":
    main()

