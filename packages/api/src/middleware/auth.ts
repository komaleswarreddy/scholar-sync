import { verifyToken } from '@clerk/clerk-sdk-node';

export async function getUserIdFromRequest(req: any) {
  const authHeader = req.headers?.authorization;

  if (!authHeader) throw new Error('Authorization header missing');

  const token = authHeader.split(' ')[1]; // Bearer <token>

  if (!token) throw new Error('JWT token missing');

  const payload = await verifyToken(token, {
    secretKey: process.env.CLERK_SECRET_KEY!,
  });

  if (!payload?.sub) throw new Error('Invalid Clerk token');

  return payload.sub; // userId
}
