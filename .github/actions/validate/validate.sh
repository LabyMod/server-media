#!/usr/bin/env bash

# Small variable to determine exit code at the end
ERRORS=0
IMAGES=0
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

FILE_NAMES=("icon.png" "icon@2x.png" "logo.png" "logo@2x.png" "background.png" "background@2x.png" "banner.png" "panorama.jpg")
REQUIRED_FILES=("manifest.json" "icon.png" "icon@2x.png")

# Small error handling method, that works with GitHub Actions
function error() {
  local file=${1}
  local message=${2}
  ((ERRORS++))

  if [[ ! -z "${GITHUB_ACTIONS}" ]]; then
    echo "::error file=${file}::${message}: ${file}"
  else
    echo "${message}: ${file}"
  fi
}

function summary() {
  [[ -z "${GITHUB_STEP_SUMMARY}" ]] && return
  echo "### Images" >> "${GITHUB_STEP_SUMMARY}"
  echo "${1}" >> "${GITHUB_STEP_SUMMARY}"
}

# Pull requests only check the server directories they touch. The workflow lists
# the changed files in changed_files.txt, without it every directory is checked.
directories=()
if [[ -f changed_files.txt ]]; then
  while IFS=$'\t' read -r status path; do
    [[ "${path}" == minecraft_servers/* ]] || continue
    relative=${path#minecraft_servers/}
    if [[ "${relative}" != */* ]]; then
      [[ "${status}" != "D" ]] && error "${path}" "Files have to be inside a server directory"
      continue
    fi
    directory="minecraft_servers/${relative%%/*}"
    [[ -d "${directory}" && ! " ${directories[*]} " =~ " ${directory} " ]] && directories+=("${directory}")
  done < changed_files.txt
else
  for path in minecraft_servers/*; do
    if [[ -d "${path}" ]]; then
      directories+=("${path}")
    else
      error "${path}" "Files have to be inside a server directory"
    fi
  done
fi

if [[ "${#directories[@]}" -eq 0 ]]; then
  echo "No server directories to check, found ${ERRORS} issues."
  summary "No server directories changed."
  [[ "${ERRORS}" -ne 0 ]] && exit 1 || exit 0
fi

# Symbolic links could point to any file outside of the repository
while IFS= read -r -d '' link; do
  error "${link}" "Symbolic links are not allowed"
done < <(find "${directories[@]}" -type l -print0)

backgrounds=()
while IFS= read -r -d '' image; do
    filename=$(basename "${image}")
    folderpath=$(dirname "${image}")
    relative=${image#minecraft_servers/*/}

    if [[ "${relative}" == "manifest.json" ]]; then
      continue
    fi

    # check for invalid file names
    if [[ "${relative}" == gamemodes/* ]]; then
      if [[ ! "${relative}" =~ ^gamemodes/[^/]+/icon\.png$ ]]; then
        error "${image}" "Invalid file, gamemodes may only contain gamemodes/{gamemode_key}/icon.png: https://github.com/LabyMod/server-media/blob/master/docs/Files.md#gamemodes"
        continue
      fi
    elif [[ "${relative}" == */* || ! " ${FILE_NAMES[*]} " =~ " ${filename} " ]]; then
      error "${image}" "Invalid file name ${filename}: https://github.com/LabyMod/server-media/blob/master/docs/Files.md#filestructure"
      continue
    fi

    # Read properties from image
    properties=($(identify -format "%w %h %m " "${image}[0]"))
    if [[ "$?" -ne 0 ]]; then
      error "${image}" "Could not read image file"
      continue
    fi

    # Extract properties into variables
    width="${properties[0]}"
    height="${properties[1]}"
    type="${properties[2]}"
    size=$(stat -c %s "${image}")  # File size in bytes

    # Check whether file is > 1.5MB
    if (( size > 1572864 )); then
      error "${image}" "The file ${filename} is larger than 1.5 MB. Please compress it on https://compresspng.com"
      continue
    fi

    # Ensure file is actually a PNG file (panorama.jpg is the only JPEG)
    if [[ "${filename}" == "panorama.jpg" ]]; then
      [[ "${type}" != "JPEG" ]] \
        && error "${image}" "Invalid file type '${type}' for file"
    elif [[ "${type}" != "PNG" ]]; then
      error "${image}" "Invalid file type '${type}' for file"
    fi

    # Ensure normal version exists when hDPI image is provided
    [[ "${filename}" == "icon@2x.png" ]] \
      && [[ ! -f "${folderpath}/icon.png" ]] \
        && error "${image}" "hDPI icon was provided, but the normal version is missing"

    [[ "${filename}" == "logo@2x.png" ]] \
      && [[ ! -f "${folderpath}/logo.png" ]] \
        && error "${image}" "hDPI logo was provided, but the normal version is missing"

    [[ "${filename}" == "background@2x.png" ]] \
      && [[ ! -f "${folderpath}/background.png" ]] \
        && error "${image}" "hDPI background was provided, but the normal version is missing"

    # Validate image dimensions
    if [[ "${relative}" == gamemodes/* ]]; then
      # gamemode icon dimension
      [[ "${width}" -ne 512 || "${height}" -ne 512 ]] \
        && error "${image}" "Invalid gamemode icon size! Size is ${width}x${height}px, must be 512x512px"

    elif [[ "${filename}" == "icon.png" ]]; then
      # icon dimension
      [[ "${width}" -ne 256 || "${height}" -ne 256 ]] \
        && error "${image}" "Invalid icon size! Size is ${width}x${height}px, must be 256x256px"

    elif [[ "${filename}" == "icon@2x.png" ]]; then
      # hDPI icon dimension
      [[ "${width}" -ne 512 || "${height}" -ne 512 ]] \
        && error "${image}" "Invalid hDPI icon size! Size is ${width}x${height}px, must be 512x512px"

    elif [[ "${filename}" == "logo.png" ]]; then
      # Minimal shortest side
      if [[ "${width}" -le "${height}" && "${width}" -lt 128 ]]; then
        error "${image}" "Invalid logo size! Size is ${width}x${height}px, shortest side must be at least 128px"
      elif [[ "${width}" -ge "${height}" && "${height}" -lt 128 ]]; then
        error "${image}" "Invalid logo size! Size is ${width}x${height}px, shortest side must be at least 128px"
      fi

      # Maximal shortest size
      if [[ "${width}" -le "${height}" && "${width}" -gt 256 ]]; then
        error "${image}" "Invalid logo size! Size is ${width}x${height}px, shortest side must not exceed 256px"
      elif [[ "${width}" -ge "${height}" && "${height}" -gt 256 ]]; then
        error "${image}" "Invalid logo size! Size is ${width}x${height}px, shortest side must not exceed 256px"
      fi

    elif [[ "${filename}" == "logo@2x.png" ]]; then
      # Minimal shortest side
      if [[ "${width}" -le "${height}" && "${width}" -lt 256 ]]; then
        error "${image}" "Invalid hDPI logo size! Size is ${width}x${height}px, shortest side must be at least 256px"
      elif [[ "${width}" -ge "${height}" && "${height}" -lt 256 ]]; then
        error "${image}" "Invalid hDPI logo size! Size is ${width}x${height}px, shortest side must be at least 256px"
      fi

      # Maximal shortest side
      if [[ "${width}" -le "${height}" && "${width}" -gt 512 ]]; then
        error "${image}" "Invalid hDPI logo size! Size is ${width}x${height}px, shortest side must not exceed 512px"
      elif [[ "${width}" -ge "${height}" && "${height}" -gt 512 ]]; then
        error "${image}" "Invalid hDPI logo size! Size is ${width}x${height}px, shortest side must not exceed 512px"
      fi

    elif [[ "${filename}" == "background.png" ]]; then
      # background dimension
      [[ "${width}" -ne 1280 || "${height}" -ne 720 ]] \
        && error "${image}" "Invalid background size! Size is ${width}x${height}px, must be 1280x720px"
      backgrounds+=("${image}")

    elif [[ "${filename}" == "background@2x.png" ]]; then
      # hDPI background dimension
      [[ "${width}" -ne 1920 || "${height}" -ne 1080 ]] \
        && error "${image}" "Invalid hDPI background size! Size is ${width}x${height}px, must be 1920x1080px"
      backgrounds+=("${image}")


    # check banner.png if it exists
    elif [[ "${filename}" == "banner.png" ]]; then
      # banner dimension
      [[ "${width}" -ne 1280 || "${height}" -ne 256 ]] \
        && error "${image}" "Invalid banner size! Size is ${width}x${height}px, must be 1280x256px"

      # aspect ratio must be 5:1
      aspect_ratio=$(echo "scale=2; ${width} / ${height}" | bc)
      [[ "${aspect_ratio}" != "5.00" ]] \
        && error "${image}" "Invalid banner aspect ratio! Aspect ratio is ${aspect_ratio}, must be 5:1"

    elif [[ "${filename}" == "panorama.jpg" ]]; then
      # equirectangular -> 2:1
      [[ $(( width )) -ne $(( height * 2 )) ]] \
        && error "${image}" "Invalid panorama aspect ratio! Size is ${width}x${height}px, must be 2:1"
    fi

    ((IMAGES++))
done < <(find "${directories[@]}" -type f -print0)

# Check the directories for required files
for dir in "${directories[@]}"; do
  for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -e "${dir}/${file}" ]; then
      error "${dir}/${file}" "${file} is not given, but it is required"
    fi
  done
done

# Bars are only a hint, a dark scene can look similar
WARNINGS=0
if [[ "${#backgrounds[@]}" -gt 0 ]]; then
  bar_output=$(python3 "${SCRIPT_DIR}/edges.py" "${backgrounds[@]}")
  if [[ -n "${bar_output}" ]]; then
    echo "${bar_output}"
    WARNINGS=$(grep -c 'warning' <<< "${bar_output}")
  fi
fi

echo ""
echo "Total of ${IMAGES} images in ${#directories[@]} directories checked, found ${ERRORS} issues and ${WARNINGS} warnings."
summary "Checked ${IMAGES} images in ${#directories[@]} server directories: ${ERRORS} errors, ${WARNINGS} warnings."

[[ "${ERRORS}" -ne 0 ]] && exit 1 || exit 0
