Repair the previous JSON response so that it validates against the requested
schema and evidence rules.

Do not add new facts. Do not remove invalid claims and present the result as
complete unless the schema marks missing or unsupported information explicitly.
Use only supplied chunks and the validation errors provided by the caller.
Return only corrected JSON.
