const REDACTION_RULES: Array<[RegExp, string]> = [
  [/\bsk-(?:proj-)?[A-Za-z0-9_-]{12,}\b/g, '<REDACTED_OPENAI_KEY>'],
  [/\bgithub_pat_[A-Za-z0-9_]{12,}\b/g, '<REDACTED_GITHUB_TOKEN>'],
  [/\bgh[pousr]_[A-Za-z0-9]{12,}\b/g, '<REDACTED_GITHUB_TOKEN>'],
  [/(Authorization\s*:\s*Bearer\s+)[^\s]+/gi, '$1<REDACTED>'],
  [/((?:password|passwd|pwd|token|secret|api[_-]?key)\s*[:=]\s*)[^\s,;]+/gi, '$1<REDACTED>']
]

export function redactSensitiveText(value: string): string {
  let output = value
  for (const [pattern, replacement] of REDACTION_RULES) output = output.replace(pattern, replacement)
  return output
}
