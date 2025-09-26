export const getAPIKey = async (userId: string) => {
  const hash = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(`${userId}clado`)
  );
  return `cl-${Buffer.from(hash).toString("hex").slice(0, 16)}`;
};
