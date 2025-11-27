"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { User, onAuthStateChanged } from "firebase/auth";
import { auth } from "@/lib/firebase";
import { registerUser } from "@/lib/api";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  isEnrolled: boolean;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  isEnrolled: false,
});

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [isEnrolled, setIsEnrolled] = useState(false);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      setUser(firebaseUser);

      if (firebaseUser) {
        try {
          const response = await registerUser();
          setIsEnrolled(response.is_enrolled);
        } catch (error) {
          console.error("Failed to sync with backend:", error);
        }
      } else {
        setIsEnrolled(false);
      }

      setLoading(false);
    });

    return () => unsubscribe();
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, isEnrolled }}>
      {children}
    </AuthContext.Provider>
  );
}
