import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';

export default function RegisterPage() {
  const [step, setStep] = useState<'access-code' | 'registration'>('access-code');
  const [accessCode, setAccessCode] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [fullName, setFullName] = useState('');
  const [institution, setInstitution] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const { setTokens } = useAuthStore();

  const handleAccessCodeSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // Simple validation - just check if something was entered
    if (!accessCode.trim()) {
      setError('Please enter an access code');
      return;
    }

    // Move to next step - actual validation happens on server
    setStep('registration');
  };

  const handleRegistrationSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // Client-side validation
    if (password !== passwordConfirm) {
      setError('Passwords do not match');
      return;
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters long');
      return;
    }

    setIsLoading(true);

    try {
      const response = await fetch('/api/auth/register-with-code', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          access_code: accessCode,
          email,
          password,
          password_confirm: passwordConfirm,
          full_name: fullName || undefined,
          institution: institution || undefined,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Registration failed');
      }

      // Registration successful! Store tokens and redirect
      if (data.access_token && data.refresh_token) {
        setTokens(data.access_token, data.refresh_token);
        navigate('/');
      } else {
        // Shouldn't happen, but just in case
        navigate('/login');
      }
    } catch (err: any) {
      setError(err.message || 'Registration failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
      <div className="bg-slate-800 rounded-lg shadow-xl p-8 w-full max-w-md border border-slate-700">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-slate-100 mb-2">
            {step === 'access-code' ? 'Access Code Required' : 'Create Account'}
          </h1>
          <p className="text-slate-400">
            {step === 'access-code'
              ? 'Enter the access code to register as a professor'
              : 'Complete your registration'}
          </p>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-900/30 border border-red-800 rounded-md text-red-400 text-sm">
            {error}
          </div>
        )}

        {step === 'access-code' ? (
          <form onSubmit={handleAccessCodeSubmit} className="space-y-6">
            <div>
              <label htmlFor="accessCode" className="block text-sm font-medium text-slate-300 mb-2">
                Access Code
              </label>
              <input
                id="accessCode"
                type="password"
                value={accessCode}
                onChange={(e) => setAccessCode(e.target.value)}
                required
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 text-slate-100 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Enter access code"
                autoComplete="off"
              />
              <p className="mt-2 text-xs text-slate-400">
                You need a valid access code to register as a professor.
              </p>
            </div>

            <button
              type="submit"
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md transition duration-200"
            >
              Continue
            </button>

            <div className="text-center">
              <a href="/login" className="text-sm text-blue-400 hover:text-blue-300">
                Already have an account? Sign in
              </a>
            </div>
          </form>
        ) : (
          <form onSubmit={handleRegistrationSubmit} className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-slate-300 mb-2">
                Email Address *
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 text-slate-100 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="prof@university.edu"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-slate-300 mb-2">
                Password *
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 text-slate-100 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="At least 8 characters"
              />
            </div>

            <div>
              <label htmlFor="passwordConfirm" className="block text-sm font-medium text-slate-300 mb-2">
                Confirm Password *
              </label>
              <input
                id="passwordConfirm"
                type="password"
                value={passwordConfirm}
                onChange={(e) => setPasswordConfirm(e.target.value)}
                required
                minLength={8}
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 text-slate-100 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Repeat password"
              />
            </div>

            <div>
              <label htmlFor="fullName" className="block text-sm font-medium text-slate-300 mb-2">
                Full Name (optional)
              </label>
              <input
                id="fullName"
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 text-slate-100 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Dr. Jane Smith"
              />
            </div>

            <div>
              <label htmlFor="institution" className="block text-sm font-medium text-slate-300 mb-2">
                Institution (optional)
              </label>
              <input
                id="institution"
                type="text"
                value={institution}
                onChange={(e) => setInstitution(e.target.value)}
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 text-slate-100 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="University Name"
              />
            </div>

            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={() => {
                  setStep('access-code');
                  setError('');
                }}
                className="flex-1 bg-slate-700 hover:bg-slate-600 text-slate-200 font-medium py-2 px-4 rounded-md transition duration-200"
              >
                Back
              </button>
              <button
                type="submit"
                disabled={isLoading}
                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md transition duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? 'Creating Account...' : 'Register'}
              </button>
            </div>

            <div className="text-center">
              <Link to="/login" className="text-sm text-blue-400 hover:text-blue-300">
                Already have an account? Sign in
              </Link>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
