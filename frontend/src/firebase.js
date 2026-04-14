import { initializeApp } from "firebase/app";
import {
  getAuth,
  sendSignInLinkToEmail,
  isSignInWithEmailLink,
  signInWithEmailLink,
  signOut,
} from "firebase/auth";

const firebaseConfig = {
  apiKey: "AIzaSyAgvJ7BUY4hzgFs8f5uRSlFF3aj4JQbJIA",
  authDomain: "doraengine-95408.firebaseapp.com",
  projectId: "doraengine-95408",
  storageBucket: "doraengine-95408.firebasestorage.app",
  messagingSenderId: "98756492724",
  appId: "1:98756492724:web:18390182b038923ea906e1",
  measurementId: "G-VZRM9D695G",
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);

const PENDING_SIGNUP_KEY = "doraengine_pending_signup";

function returnUrl() {
  return window.location.origin + window.location.pathname;
}

export async function sendVerificationEmail({ email, password, mobile }) {
  const actionCodeSettings = {
    url: returnUrl(),
    handleCodeInApp: true,
  };
  await sendSignInLinkToEmail(auth, email, actionCodeSettings);
  localStorage.setItem(
    PENDING_SIGNUP_KEY,
    JSON.stringify({ email, password, mobile }),
  );
}

export function isReturningFromEmailLink() {
  return isSignInWithEmailLink(auth, window.location.href);
}

export function readPendingSignup() {
  try {
    const raw = localStorage.getItem(PENDING_SIGNUP_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function clearPendingSignup() {
  localStorage.removeItem(PENDING_SIGNUP_KEY);
}

export async function completeEmailLinkVerification(email, linkUrl = null) {
  const url = linkUrl || window.location.href;
  await signInWithEmailLink(auth, email, url);
  try { await signOut(auth); } catch { /* session not needed after verification */ }
  history.replaceState({}, document.title, returnUrl());
}
