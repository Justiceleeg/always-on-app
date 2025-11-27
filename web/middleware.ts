import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  // Note: Full auth checking requires client-side Firebase
  // This middleware provides basic route protection structure
  // The actual auth state is verified client-side in components
  return NextResponse.next();
}

export const config = {
  matcher: ["/chat/:path*", "/login", "/register"],
};
