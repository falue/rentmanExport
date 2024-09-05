#!/bin/bash

# Change to the directory where the script is located
cd "$(dirname "$0")"

# ANSI escape codes for colors and formatting
BLUE_BG_WHITE_TEXT="\033[44;97;30m"  # Blue background, white text
GREEN_BG_BLACK_TEXT="\033[42;97;1m"  # Green background, black text
YELLOW_BG_BLACK_TEXT="\033[43;30m"   # Yellow background, black text
RED_BG_WHITE_TEXT="\033[41;97;1m"    # Red background, white text
WHITE_BG_BLACK_TEXT="\033[47;30m"    # White background, black text
RESET="\033[0m"                      # Reset all formatting

# Function to check authentication and internet connection
check_auth() {
    python3 checkAuth.py
    if [ $? -ne 0 ]; then
        echo "-------------------------------"
        echo "🚫 No internet connection or API authentication failed. Please check your connection."
        echo "-------------------------------"
        echo " "
        read -p "Press ENTER to retry…"
        return 1
    else
        return 0
    fi
}

# Function to prompt for overwrite confirmation
prompt_overwrite() {
    while true; do
        echo -ne "    ❔ ${RED_BG_WHITE_TEXT} OVERWRITE ${RESET} existing files? ${WHITE_BG_BLACK_TEXT} Y ${RESET}/${WHITE_BG_BLACK_TEXT} N ${RESET}: " 
        read overwrite
        case $overwrite in
            [Yy]* ) return 0;;  # Overwrite files
            [Nn]* ) return 1;;  # Do not overwrite files
            * ) echo "    ❌ Invalid input. Please answer y or n.";;
        esac
    done
}

# Function to prompt for export options
prompt_export() {
    while true; do
        echo -ne "Export ${BLUE_BG_WHITE_TEXT} EVERYTHING ${RESET}?       ${WHITE_BG_BLACK_TEXT} Y ${RESET}/${WHITE_BG_BLACK_TEXT} N ${RESET}: " 
        read export_all
        case $export_all in
            [Yy]* )
                # Prompt for overwrite confirmation
                if prompt_overwrite; then
                    echo -e "    Press ${WHITE_BG_BLACK_TEXT} CTRL ${RESET} and ${WHITE_BG_BLACK_TEXT} C ${RESET} to abort."
                    echo "-------------------------------"
                    python3 collectEverything.py  --overwrite
                else
                    echo -e "    Press ${WHITE_BG_BLACK_TEXT} CTRL ${RESET} and ${WHITE_BG_BLACK_TEXT} C ${RESET} to abort."
                    echo "-------------------------------"
                    python3 collectEverything.py
                fi
                return 0;;  # Exit after successful export
            [Nn]* )
                # Loop to ask for specific article number or range
                while true; do
                    echo -ne "Export ${GREEN_BG_BLACK_TEXT} SPECIFIC ${RESET} article? ${WHITE_BG_BLACK_TEXT} NUMBER ${RESET}/${WHITE_BG_BLACK_TEXT} N ${RESET}: " 
                    read article_id
                    if [[ "$article_id" =~ ^[0-9]+$ ]]; then
                        # User entered a specific article number
                        if prompt_overwrite; then
                            echo -e "    Press ${WHITE_BG_BLACK_TEXT} CTRL ${RESET} and ${WHITE_BG_BLACK_TEXT} C ${RESET} to abort."
                            echo "-------------------------------"
                            python3 collectEverything.py  --id "$article_id" --overwrite
                        else
                            echo -e "    Press ${WHITE_BG_BLACK_TEXT} CTRL ${RESET} and ${WHITE_BG_BLACK_TEXT} C ${RESET} to abort."
                            echo "-------------------------------"
                            python3 collectEverything.py  --id "$article_id"
                        fi
                        return 0  # Exit after successful export
                    elif [[ "$article_id" =~ ^[Nn]$ ]]; then
                        # User chooses not to export a specific article, ask for range
                        while true; do
                            echo -ne "Export ${YELLOW_BG_BLACK_TEXT} RANGE ${RESET}?            ${WHITE_BG_BLACK_TEXT} FROM ${RESET}-${WHITE_BG_BLACK_TEXT} TO ${RESET} or ${WHITE_BG_BLACK_TEXT} ENTER ${RESET} to abort: "
                            read range
                            # Check if input is empty
                            if [[ -z "$range" ]]; then
                                return 0  # Exit this function and return to the main loop to start over
                            fi
                            if [[ "$range" =~ ^[0-9]+-[0-9]+$ ]]; then
                                # Extract the 'from' and 'to' values
                                IFS='-' read -r start end <<< "$range"
                                num=$((end - start + 1))
                                if prompt_overwrite; then
                                    echo -e "    Press ${WHITE_BG_BLACK_TEXT} CTRL ${RESET} and ${WHITE_BG_BLACK_TEXT} C ${RESET} to abort."
                                    echo "-------------------------------"
                                    python3 collectEverything.py  --start "$start" --num "$num" --overwrite
                                else
                                    echo -e "    Press ${WHITE_BG_BLACK_TEXT} CTRL ${RESET} and ${WHITE_BG_BLACK_TEXT} C ${RESET} to abort."
                                    echo "-------------------------------"
                                    python3 collectEverything.py  --start "$start" --num "$num"
                                fi
                                return 0  # Exit after successful export
                            else
                                echo "    ❌ Invalid input. Please enter a valid range in the format 'from-to'."
                            fi
                        done
                    else
                        echo "    ❌ Invalid input. Please enter a number or 'n'."
                    fi
                done;;
            * ) echo "    ❌ Invalid input. Please answer y or n.";;
        esac
    done
}

# Main loop to ensure the script runs again after every execution
# and to check authentication and run the export process
while true; do
    check_auth  # Check internet and authentication
    if [ $? -eq 0 ]; then
        prompt_export
        echo "Process complete ✅"
        echo "-------------------------------"
        echo ""
    fi
done