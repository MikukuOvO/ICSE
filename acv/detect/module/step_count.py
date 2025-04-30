#!/usr/bin/env python3
"""
This script scans a parent directory, processes markdown files in each immediate subfolder,
searches for patterns like '==================== Step X ====================',
and outputs a separate JSON file for each subfolder.
"""

import os
import re
import json
import argparse
from collections import defaultdict


def count_steps_in_file(file_path):
    """
    Counts step patterns in a single markdown file.
    
    Args:
        file_path: Path to the markdown file
        
    Returns:
        A list of step numbers found in the file
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Pattern to match '==================== Step X ===================='
        pattern = r'====================\s+Step\s+(\d+)\s+===================='
        matches = re.findall(pattern, content)
        
        # Convert matched step numbers to integers
        step_numbers = [int(match) for match in matches]
        return step_numbers
        
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")
        return []


def process_markdown_folder(folder_path):
    """
    Process all markdown files in the given folder (non-recursively).
    
    Args:
        folder_path: Path to the folder containing markdown files
        
    Returns:
        Dictionary with statistics about steps found
    """
    if not os.path.isdir(folder_path):
        print(f"Error: {folder_path} is not a valid directory")
        return {}
    
    folder_path = os.path.join(os.path.abspath(folder_path), 'logs')
    
    all_steps = []
    file_summary = defaultdict(list)
    
    # Process each markdown file in the folder (not recursively)
    for filename in os.listdir(folder_path):
        if filename.endswith('.md'):
            file_path = os.path.join(folder_path, filename)
            steps = count_steps_in_file(file_path)
            
            if steps:
                all_steps.extend(steps)
                file_summary[filename] = steps
    
    # Prepare the results
    results = {
        'folder_name': os.path.basename(folder_path),
        'folder_path': folder_path,
        'total_files_processed': len(file_summary),
        'total_steps_found': len(all_steps),
        'unique_steps': sorted(set(all_steps)),
        'step_count': len(set(all_steps)),
        'file_summary': dict(file_summary)
    }
    
    return results


def process_parent_directory(parent_dir, output_dir):
    """
    Process each immediate subfolder in the parent directory
    and create a JSON file for each one.
    
    Args:
        parent_dir: Path to the parent directory
        output_dir: Directory to save JSON output files
    
    Returns:
        Summary of processing results
    """
    if not os.path.isdir(parent_dir):
        print(f"Error: {parent_dir} is not a valid directory")
        return {}
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    summary = {
        'total_subfolders': 0,
        'total_files_processed': 0,
        'total_steps_found': 0,
        'subfolders_with_steps': 0,
        'all_unique_steps': set(),
        'subfolder_results': {}
    }
    
    # Get immediate subfolders
    subfolders = [f.path for f in os.scandir(parent_dir) if f.is_dir()]
    
    # Process each subfolder
    for subfolder in subfolders:
        subfolder_name = os.path.basename(subfolder)
        print(f"Processing subfolder: {subfolder_name}")
        
        # Skip output directory if it's a direct subfolder
        if os.path.abspath(subfolder) == os.path.abspath(output_dir):
            continue
            
        results = process_markdown_folder(subfolder)
        
        # Skip folders with no markdown files or no step patterns
        if not results or results['total_steps_found'] == 0:
            print(f"  No step patterns found in {subfolder_name}")
            continue
            
        # Update summary
        summary['total_subfolders'] += 1
        summary['total_files_processed'] += results['total_files_processed']
        summary['total_steps_found'] += results['total_steps_found']
        summary['subfolders_with_steps'] += 1
        summary['all_unique_steps'].update(results['unique_steps'])
        
        # Store basic information in the summary
        summary['subfolder_results'][subfolder_name] = {
            'total_files': results['total_files_processed'],
            'total_steps': results['total_steps_found'],
            'unique_steps': results['unique_steps']
        }
        
        # Create JSON file for this subfolder
        output_file = os.path.join(output_dir, f"{subfolder_name}_steps.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
            
        print(f"  Created: {output_file}")
    
    # Convert set to sorted list for JSON serialization
    summary['all_unique_steps'] = sorted(summary['all_unique_steps'])
    
    # Create a summary JSON file
    summary_file = os.path.join(output_dir, "summary.json")
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
        
    print(f"Created summary file: {summary_file}")
    
    return summary


def main():
    # Set up command line arguments
    parser = argparse.ArgumentParser(
        description='Process markdown files in each subfolder and create JSON outputs.')
    parser.add_argument('--parent_dir', default='acv/results/social-network/user-timeline', help='Parent directory containing subfolders to process')
    parser.add_argument('--output', '-o', default='step_results', 
                        help='Directory to save JSON output files (default: step_results)')
    
    args = parser.parse_args()
    
    # Process the parent directory
    summary = process_parent_directory(args.parent_dir, args.output)
    
    if not summary:
        return
    
    # Display the final summary
    print(f"\nProcessing complete for {args.parent_dir}:")
    print(f"Found {summary['subfolders_with_steps']} subfolders containing step patterns")
    print(f"Processed {summary['total_files_processed']} markdown files total")
    print(f"Found {summary['total_steps_found']} step markers total")
    print(f"Found {len(summary['all_unique_steps'])} unique step numbers across all subfolders")
    print(f"All results saved to: {args.output}/")


if __name__ == "__main__":
    main()