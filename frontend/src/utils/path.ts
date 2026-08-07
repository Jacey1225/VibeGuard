/** Normalizes a repository-relative path to forward-slash form for display and comparison. */
export function normalizeRelativePath(relativePath: string): string {
  return relativePath.replace(/\\/g, "/");
}
