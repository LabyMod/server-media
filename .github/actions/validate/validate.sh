#!/usr/bin/env bash

# Small variable to determine exit code at the end
ERRORS=0
IMAGES=0

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

given_names=()
# Find all files in the src folder
while read image; do
    filename=$(basename "${image}")
    folderpath=$(dirname "${image}")
    # foldername=$(basename "${folderpath}")

    if [[ "${filename}" == "manifest.json" ]]; then
      continue
    fi

    # Read properties from image
    properties=($(identify -format "%w %h %m" "${image}"))
    if [[ "$?" -ne 0 ]]; then
      error "${image}" "Could not read image file"
      continue
    fi

    # Extract properties into variables
    width="${properties[0]}"
    height="${properties[1]}"
    type="${properties[2]}"

    # Ensure file is actually a PNG file
    [[ "${type}" != "PNG" ]] \
      && error "${image}" "Invalid file type '${type}' for file"

    given_names+=("${filename}")

    # check for invalid file names
    filenames=("icon.png" "icon@2x.png" "logo.png" "logo@2x.png" "background.png" "background@2x.png" "banner.png")
    if [[ ! " ${filenames[@]} " =~ " ${filename} " && "${folderpath}" != *"gamemodes"* ]]; then
        error "${image}" "Invalid file name ${filename}: https://github.com/LabyMod/server-media/blob/master/docs/Files.md#filestructure"
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
    if [[ "${filename}" == "icon.png" && "${folderpath}" != *"gamemodes"* ]]; then
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

    elif [[ "${filename}" == "background@2x.png" ]]; then
      # hDPI background dimension
      [[ "${width}" -ne 1920 || "${height}" -ne 1080 ]] \
        && error "${image}" "Invalid hDPI background size! Size is ${width}x${height}px, must be 1920x1080px"


    # check banner.png if it exists
    elif [[ "${filename}" == "banner.png" ]]; then
      # banner dimension
      [[ "${width}" -ne 1280 || "${height}" -ne 256 ]] \
        && error "${image}" "Invalid banner size! Size is ${width}x${height}px, must be 1280x256px"

      # aspect ratio must be 5:1
      aspect_ratio=$(echo "scale=2; ${width} / ${height}" | bc)
      [[ "${aspect_ratio}" != "5.00" ]] \
        && error "${image}" "Invalid banner aspect ratio! Aspect ratio is ${aspect_ratio}, must be 5:1"
    fi

    ((IMAGES++))
done <<< $(find minecraft_servers -type f)

if [[ ! "${given_names[@]}" =~ "icon.png" || ! "${given_names[@]}" =~ "icon@2x.png" ]]; then
  error "At least one of the required files is not given (icon.png or icon@2x.png)"
fi

echo ""
echo "Total of ${IMAGES} images checked, found ${ERRORS} issues."

[[ "${ERRORS}" -ne 0 ]] && exit 1 || exit 0
