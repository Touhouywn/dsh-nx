export const name = 'dsh-nx'

/**
 * Host half is intentionally empty: the NX capability arrives through the
 * `nx` MCP server registered by this bundle's cordis.patch.yml, and the UI
 * arrives through the `./client` bundle.
 */
export function apply() {}
