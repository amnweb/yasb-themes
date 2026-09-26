Contributing

Please read these short instructions before submitting a theme. Submit themes using the "Submit a theme" issue template (do NOT open PRs manually). The project automation will parse your issue and create a PR.

Quick rejection reasons (maintainers will reject or request fixes for):
- Inconsistent or unreadable colors.
- Missing or broken configuration fields.
- Poor contrast or layout issues.
- Not following the required file naming / structure conventions.
- Excessive commented-out code or very large commented blocks in files.
- Missing or broken theme screenshot, or one that was not taken with the YASB screenshot tool.
- Missing or very poor `About` text or preview images.
- Not following the required formatting for `config.yaml` (e.g. missing fields, incorrect indentation, etc.).
- Bad UI choices (e.g. using a very small font size, using a very large font size, using a very small or very large bar height, etc.).
- Quality of the theme is not up to the standards of the gallery.
- Submitting a theme that is very similar to an existing theme without significant improvements or differences.
- Submitting a theme that is not original or is a copy of an existing theme without proper attribution.
- Submitting a theme that is not compatible with the latest version of YASB or has known bugs that have not been fixed.
- Submitting a theme that does not follow the required file structure or naming conventions.

Theme screenshot:
- Take the screenshot with the tool built into YASB: right-click an empty part of the bar and choose "Take Screenshot". If the menu does not open, check that `context_menu` is not set to `false` for the bar in your `config.yaml`.
- The screenshot is saved as a PNG in your `Pictures\YASB_Screenshots` folder.
- Upload that PNG in the `Theme screenshot` field of the form (drag and drop it, or click to choose it). Only one image is accepted.

README:
- The README is created for you from the `About`, `Requirements` and `Preview images` fields. The list of widgets the theme uses is added automatically from your config.
- Upload 1 to 5 PNG or JPG images in `Preview images`. They are stored with your theme, converted to JPG and scaled down to at most 3840 px on the longest side.

Checklist before opening the issue:
- Put your final `config.yaml` and `styles.css` in one ZIP file and upload it in the `Theme files` field. Keep the config well formatted and leave out big commented blocks.
- Upload your YASB screenshot (one PNG) in the `Theme screenshot` field.
- Write a few words about your theme in `About`, list what it needs besides YASB (fonts, tools or apps) in `Requirements` and upload 1 to 5 images in `Preview images`.

If a submission is rejected the maintainers will leave a clear comment explaining what to fix; PRs may be closed after 14 days without response.

Keeping themes compatible with YASB:
- Pull requests that change a theme are checked automatically against the latest YASB release, and the result is posted as a comment on the pull request.
- All themes are checked against the latest YASB release every day. If your theme fails, an issue is opened that mentions you and lists what needs to change.
- If the theme still fails 7 days after the issue was opened, and there is no open pull request for it, the theme is disabled in the theme gallery. The issue shows the exact date. It is re-enabled automatically once a fix is merged and the theme passes the check again.

Thank you for contributing - clean, readable themes make the gallery better for everyone.
