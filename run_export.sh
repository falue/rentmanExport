#!/bin/bash

# Function to prompt for overwrite confirmation
prompt_overwrite() {
    while true; do
        read -p "  ❔ Overwrite existing files? y/n: " overwrite
        case $overwrite in
            [Yy]* ) return 0;;  # Overwrite files
            [Nn]* ) return 1;;  # Do not overwrite files
            * ) echo "  ❌ Invalid input. Please answer y or n.";;
        esac
    done
    echo "  🏃 Running.."
    echo "-------------------------------"
}

# Function to prompt for export options
prompt_export() {
    while true; do
        read -p "Export everything? y/n: " export_all
        case $export_all in
            [Yy]* )
                # Prompt for overwrite confirmation
                if prompt_overwrite; then
                    python3 collectEverything.py  --overwrite
                else
                    python3 collectEverything.py
                fi
                return 0;;  # Exit after successful export
            [Nn]* )
                # Loop to ask for specific article number or range
                while true; do
                    read -p "Export specific article? number/n: " article_id
                    if [[ "$article_id" =~ ^[0-9]+$ ]]; then
                        # User entered a specific article number
                        if prompt_overwrite; then
                            python3 collectEverything.py  --id "$article_id" --overwrite
                        else
                            python3 collectEverything.py  --id "$article_id"
                        fi
                        return 0  # Exit after successful export
                    elif [[ "$article_id" =~ ^[Nn]$ ]]; then
                        # User chooses not to export a specific article, ask for range
                        while true; do
                            read -p "Export range? from-to: " range
                            if [[ "$range" =~ ^[0-9]+-[0-9]+$ ]]; then
                                # Extract the 'from' and 'to' values
                                IFS='-' read -r start end <<< "$range"
                                num=$((end - start + 1))
                                if prompt_overwrite; then
                                    python3 collectEverything.py  --start "$start" --num "$num" --overwrite
                                else
                                    python3 collectEverything.py  --start "$start" --num "$num"
                                fi
                                return 0  # Exit after successful export
                            else
                                echo "  ❌ Invalid input. Please enter a valid range in the format 'from-to'."
                            fi
                        done
                    else
                        echo "  ❌ Invalid input. Please enter a number or 'n'."
                    fi
                done;;
            * ) echo "  ❌ Invalid input. Please answer y or n.";;
        esac
    done
}

# Main loop to ensure the script runs again after every execution
while true; do
    prompt_export
    echo "Process complete ✅"
    echo "-------------------------------"
    echo ""
done
