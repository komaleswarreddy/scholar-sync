'use client';

import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Loader2, Pencil, Search, Trash2, UserCog, UserX } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { useAdminAccounts } from '@/hooks/useAdminAccounts';
import { AdminTableSkeleton } from '@/components/skeleton';
import type { PlatformUser } from '@/lib/platform-auth';

const ROLES = ['student', 'teacher', 'expert', 'schooladmin'] as const;
const EXPERTISE_TIERS = ['', 'student', 'teacher', 'tutor', 'sme'] as const;

const ROLE_BADGE: Record<string, string> = {
  student: 'bg-gray-100 text-gray-700',
  teacher: 'bg-purple-100 text-purple-700',
  expert: 'bg-amber-100 text-amber-800',
  schooladmin: 'bg-blue-100 text-blue-700',
};

function RoleBadge({ role }: { role: string }) {
  const cls = ROLE_BADGE[role] ?? ROLE_BADGE.student;
  return (
    <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${cls}`}>
      {role}
    </span>
  );
}

function displayName(user: PlatformUser) {
  const parts = [user.first_name, user.last_name].filter(Boolean);
  if (parts.length) return parts.join(' ');
  return user.username ?? '—';
}

export default function RolesPermissionsPage() {
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [formError, setFormError] = useState<string | null>(null);
  const [formSuccess, setFormSuccess] = useState<string | null>(null);

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('student');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [mobile, setMobile] = useState('');
  const [institute, setInstitute] = useState('');
  const [classLevel, setClassLevel] = useState('');
  const [expertiseTier, setExpertiseTier] = useState('');

  const [editingUser, setEditingUser] = useState<PlatformUser | null>(null);
  const [editRole, setEditRole] = useState('student');
  const [editExpertiseTier, setEditExpertiseTier] = useState('');
  const [editFirstName, setEditFirstName] = useState('');
  const [editLastName, setEditLastName] = useState('');
  const [editEmail, setEditEmail] = useState('');
  const [editMobile, setEditMobile] = useState('');
  const [editInstitute, setEditInstitute] = useState('');
  const [editClassLevel, setEditClassLevel] = useState('');
  const [editPassword, setEditPassword] = useState('');
  const [editError, setEditError] = useState<string | null>(null);
  const [rowActionId, setRowActionId] = useState<string | null>(null);

  const { listQuery, createMutation, updateMutation, deleteMutation, ready } = useAdminAccounts(search, roleFilter || undefined);

  const accounts = useMemo(() => listQuery.data?.items ?? [], [listQuery.data]);

  useEffect(() => {
    if (!editingUser) return;
    setEditRole(editingUser.role || 'student');
    setEditFirstName(editingUser.first_name ?? '');
    setEditLastName(editingUser.last_name ?? '');
    setEditEmail(editingUser.email ?? '');
    setEditMobile(editingUser.mobile ?? '');
    setEditInstitute(editingUser.institute ?? '');
    setEditClassLevel(editingUser.class_level ?? '');
    setEditExpertiseTier(editingUser.expertise_tier ?? '');
    setEditPassword('');
    setEditError(null);
  }, [editingUser]);

  const resetForm = () => {
    setUsername('');
    setPassword('');
    setRole('student');
    setFirstName('');
    setLastName('');
    setEmail('');
    setMobile('');
    setInstitute('');
    setClassLevel('');
    setExpertiseTier('');
  };

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setFormSuccess(null);
    try {
      await createMutation.mutateAsync({
        username: username.trim(),
        password,
        role: role || 'student',
        first_name: firstName.trim() || undefined,
        last_name: lastName.trim() || undefined,
        email: email.trim() || undefined,
        mobile: mobile.trim() || undefined,
        institute: institute.trim() || undefined,
        class_level: classLevel.trim() || undefined,
        expertise_tier: expertiseTier.trim() || undefined,
      });
      setFormSuccess(`Account "${username.trim()}" created successfully.`);
      resetForm();
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (err as Error)?.message ||
        'Failed to create account';
      setFormError(typeof detail === 'string' ? detail : 'Failed to create account');
    }
  };

  const handleEditSave = async (e: FormEvent) => {
    e.preventDefault();
    if (!editingUser) return;
    setEditError(null);
    try {
      await updateMutation.mutateAsync({
        id: editingUser.id,
        data: {
          role: editRole,
          first_name: editFirstName.trim() || undefined,
          last_name: editLastName.trim() || undefined,
          email: editEmail.trim() || undefined,
          mobile: editMobile.trim() || undefined,
          institute: editInstitute.trim() || undefined,
          class_level: editClassLevel.trim() || undefined,
          expertise_tier: editExpertiseTier.trim() || undefined,
          ...(editPassword.trim().length >= 8 ? { password: editPassword } : {}),
        },
      });
      setFormSuccess(`Account "${editingUser.username}" updated.`);
      setEditingUser(null);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (err as Error)?.message ||
        'Failed to update account';
      setEditError(typeof detail === 'string' ? detail : 'Failed to update account');
    }
  };

  const handleToggleActive = async (user: PlatformUser) => {
    const nextActive = user.is_active === false;
    const label = nextActive ? 'reactivate' : 'deactivate';
    if (!window.confirm(`${label.charAt(0).toUpperCase() + label.slice(1)} "${user.username}"?`)) return;
    setRowActionId(user.id);
    try {
      await updateMutation.mutateAsync({
        id: user.id,
        data: { is_active: nextActive },
      });
      setFormSuccess(`Account "${user.username}" ${nextActive ? 'reactivated' : 'deactivated'}.`);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (err as Error)?.message ||
        'Failed to update account status';
      setFormError(typeof detail === 'string' ? detail : 'Failed to update account status');
    } finally {
      setRowActionId(null);
    }
  };

  const handleDelete = async (user: PlatformUser) => {
    if (
      !window.confirm(
        `Permanently delete "${user.username}"? This cannot be undone. Use Deactivate if you only want to block login.`
      )
    ) {
      return;
    }
    setRowActionId(user.id);
    try {
      await deleteMutation.mutateAsync(user.id);
      if (editingUser?.id === user.id) setEditingUser(null);
      setFormSuccess(`Account "${user.username}" deleted.`);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (err as Error)?.message ||
        'Failed to delete account';
      setFormError(typeof detail === 'string' ? detail : 'Failed to delete account');
    } finally {
      setRowActionId(null);
    }
  };

  if (!ready || listQuery.isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-semibold text-text-primary">Roles & Permissions</h1>
        <AdminTableSkeleton rows={6} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <UserCog className="w-7 h-7 text-accent-blue" />
        <div>
          <h1 className="text-2xl font-semibold text-text-primary">Roles & Permissions</h1>
          <p className="text-sm text-text-secondary mt-0.5">
            Create accounts for students, teachers, experts, and school admins.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[380px_1fr] gap-6">
        <div className="rounded-xl border border-border-default bg-white p-6 shadow-sm h-fit">
          <h2 className="text-lg font-semibold text-text-primary mb-4">Create Account</h2>

          {formError && (
            <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {formError}
            </div>
          )}
          {formSuccess && (
            <div className="mb-4 rounded-lg border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-700">
              {formSuccess}
            </div>
          )}

          <form onSubmit={handleCreate} className="space-y-3">
            <div>
              <label className="mb-1 block text-sm font-medium text-text-primary">
                Username <span className="text-red-500">*</span>
              </label>
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                className="w-full rounded-lg border border-border-default px-3 py-2 text-sm outline-none focus:border-accent-blue focus:ring-2 focus:ring-accent-blue/20"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-text-primary">
                Password <span className="text-red-500">*</span>
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                className="w-full rounded-lg border border-border-default px-3 py-2 text-sm outline-none focus:border-accent-blue focus:ring-2 focus:ring-accent-blue/20"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-text-primary">Role</label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="w-full rounded-lg border border-border-default px-3 py-2 text-sm outline-none focus:border-accent-blue focus:ring-2 focus:ring-accent-blue/20"
              >
                {ROLES.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-text-secondary">Expertise tier (IIL)</label>
              <select
                value={expertiseTier}
                onChange={(e) => setExpertiseTier(e.target.value)}
                className="w-full rounded-lg border border-border-default px-3 py-2 text-sm outline-none focus:border-accent-blue focus:ring-2 focus:ring-accent-blue/20"
              >
                {EXPERTISE_TIERS.map((t) => (
                  <option key={t || 'default'} value={t}>
                    {t ? t : 'Default (from role)'}
                  </option>
                ))}
              </select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block text-sm font-medium text-text-secondary">First name</label>
                <input
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  className="w-full rounded-lg border border-border-default px-3 py-2 text-sm outline-none focus:border-accent-blue focus:ring-2 focus:ring-accent-blue/20"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-text-secondary">Last name</label>
                <input
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  className="w-full rounded-lg border border-border-default px-3 py-2 text-sm outline-none focus:border-accent-blue focus:ring-2 focus:ring-accent-blue/20"
                />
              </div>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-text-secondary">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-lg border border-border-default px-3 py-2 text-sm outline-none focus:border-accent-blue focus:ring-2 focus:ring-accent-blue/20"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-text-secondary">Mobile</label>
              <input
                value={mobile}
                onChange={(e) => setMobile(e.target.value)}
                className="w-full rounded-lg border border-border-default px-3 py-2 text-sm outline-none focus:border-accent-blue focus:ring-2 focus:ring-accent-blue/20"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-text-secondary">Institute</label>
              <input
                value={institute}
                onChange={(e) => setInstitute(e.target.value)}
                className="w-full rounded-lg border border-border-default px-3 py-2 text-sm outline-none focus:border-accent-blue focus:ring-2 focus:ring-accent-blue/20"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-text-secondary">Class</label>
              <input
                value={classLevel}
                onChange={(e) => setClassLevel(e.target.value)}
                placeholder="e.g. Class 11"
                className="w-full rounded-lg border border-border-default px-3 py-2 text-sm outline-none focus:border-accent-blue focus:ring-2 focus:ring-accent-blue/20"
              />
            </div>
            <Button type="submit" disabled={createMutation.isPending} className="w-full">
              {createMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  Creating…
                </>
              ) : (
                'Create Account'
              )}
            </Button>
          </form>
        </div>

        <div className="rounded-xl border border-border-default bg-white shadow-sm overflow-hidden">
          <div className="p-4 border-b border-border-default flex flex-col sm:flex-row gap-3 sm:items-center sm:justify-between">
            <h2 className="text-lg font-semibold text-text-primary">Accounts</h2>
            <div className="flex flex-col sm:flex-row gap-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-tertiary" />
                <Input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search users…"
                  className="pl-9 w-full sm:w-48"
                />
              </div>
              <select
                value={roleFilter}
                onChange={(e) => setRoleFilter(e.target.value)}
                className="rounded-lg border border-border-default px-3 py-2 text-sm"
              >
                <option value="">All roles</option>
                {ROLES.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-surface border-b border-border-default">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-text-secondary">Name</th>
                  <th className="text-left px-4 py-3 font-medium text-text-secondary">Username</th>
                  <th className="text-left px-4 py-3 font-medium text-text-secondary">Role</th>
                  <th className="text-left px-4 py-3 font-medium text-text-secondary">Email</th>
                  <th className="text-left px-4 py-3 font-medium text-text-secondary">Mobile</th>
                  <th className="text-left px-4 py-3 font-medium text-text-secondary">Institute</th>
                  <th className="text-left px-4 py-3 font-medium text-text-secondary">Class</th>
                  <th className="text-left px-4 py-3 font-medium text-text-secondary">Status</th>
                  <th className="text-left px-4 py-3 font-medium text-text-secondary">Actions</th>
                </tr>
              </thead>
              <tbody>
                {accounts.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="px-4 py-8 text-center text-text-tertiary">
                      No accounts yet. Create one using the form.
                    </td>
                  </tr>
                ) : (
                  accounts.map((user) => (
                    <tr key={user.id} className="border-b border-border-default hover:bg-surface-hover">
                      <td className="px-4 py-3 text-text-primary">{displayName(user)}</td>
                      <td className="px-4 py-3 font-mono text-text-secondary">{user.username}</td>
                      <td className="px-4 py-3">
                        <RoleBadge role={user.role} />
                      </td>
                      <td className="px-4 py-3 text-text-secondary">{user.email ?? '—'}</td>
                      <td className="px-4 py-3 text-text-secondary">{user.mobile ?? '—'}</td>
                      <td className="px-4 py-3 text-text-secondary">{user.institute ?? '—'}</td>
                      <td className="px-4 py-3 text-text-secondary">{user.class_level ?? '—'}</td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${
                            user.is_active === false
                              ? 'bg-red-100 text-red-700'
                              : 'bg-green-100 text-green-700'
                          }`}
                        >
                          {user.is_active === false ? 'Inactive' : 'Active'}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => setEditingUser(user)}
                            className="inline-flex items-center gap-1 rounded-md border border-border-default px-2 py-1 text-xs text-text-secondary hover:bg-surface-hover"
                          >
                            <Pencil className="w-3 h-3" />
                            Edit
                          </button>
                          <button
                            type="button"
                            disabled={rowActionId === user.id}
                            onClick={() => void handleToggleActive(user)}
                            className="inline-flex items-center gap-1 rounded-md border border-border-default px-2 py-1 text-xs text-text-secondary hover:bg-surface-hover disabled:opacity-50"
                          >
                            {rowActionId === user.id ? (
                              <Loader2 className="w-3 h-3 animate-spin" />
                            ) : (
                              <UserX className="w-3 h-3" />
                            )}
                            {user.is_active === false ? 'Activate' : 'Deactivate'}
                          </button>
                          <button
                            type="button"
                            disabled={rowActionId === user.id || deleteMutation.isPending}
                            onClick={() => void handleDelete(user)}
                            className="inline-flex items-center gap-1 rounded-md border border-red-200 px-2 py-1 text-xs text-red-600 hover:bg-red-50 disabled:opacity-50"
                          >
                            {rowActionId === user.id && deleteMutation.isPending ? (
                              <Loader2 className="w-3 h-3 animate-spin" />
                            ) : (
                              <Trash2 className="w-3 h-3" />
                            )}
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {editingUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-lg rounded-xl border border-border-default bg-white p-6 shadow-xl">
            <h2 className="text-lg font-semibold text-text-primary mb-1">Edit account</h2>
            <p className="text-sm text-text-secondary mb-4 font-mono">{editingUser.username}</p>
            {editError && (
              <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                {editError}
              </div>
            )}
            <form onSubmit={handleEditSave} className="space-y-3">
              <div>
                <label className="mb-1 block text-sm font-medium text-text-primary">Role</label>
                <select
                  value={editRole}
                  onChange={(e) => setEditRole(e.target.value)}
                  className="w-full rounded-lg border border-border-default px-3 py-2 text-sm"
                >
                  {ROLES.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-text-primary">Expertise tier (IIL)</label>
                <select
                  value={editExpertiseTier}
                  onChange={(e) => setEditExpertiseTier(e.target.value)}
                  className="w-full rounded-lg border border-border-default px-3 py-2 text-sm"
                >
                  {EXPERTISE_TIERS.map((t) => (
                    <option key={t || 'default'} value={t}>
                      {t ? t : 'Default (from role)'}
                    </option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <input
                  value={editFirstName}
                  onChange={(e) => setEditFirstName(e.target.value)}
                  placeholder="First name"
                  className="w-full rounded-lg border border-border-default px-3 py-2 text-sm"
                />
                <input
                  value={editLastName}
                  onChange={(e) => setEditLastName(e.target.value)}
                  placeholder="Last name"
                  className="w-full rounded-lg border border-border-default px-3 py-2 text-sm"
                />
              </div>
              <input
                type="email"
                value={editEmail}
                onChange={(e) => setEditEmail(e.target.value)}
                placeholder="Email"
                className="w-full rounded-lg border border-border-default px-3 py-2 text-sm"
              />
              <input
                value={editMobile}
                onChange={(e) => setEditMobile(e.target.value)}
                placeholder="Mobile"
                className="w-full rounded-lg border border-border-default px-3 py-2 text-sm"
              />
              <input
                value={editInstitute}
                onChange={(e) => setEditInstitute(e.target.value)}
                placeholder="Institute"
                className="w-full rounded-lg border border-border-default px-3 py-2 text-sm"
              />
              <input
                value={editClassLevel}
                onChange={(e) => setEditClassLevel(e.target.value)}
                placeholder="Class"
                className="w-full rounded-lg border border-border-default px-3 py-2 text-sm"
              />
              <input
                type="password"
                value={editPassword}
                onChange={(e) => setEditPassword(e.target.value)}
                placeholder="New password (optional, min 8 chars)"
                minLength={8}
                className="w-full rounded-lg border border-border-default px-3 py-2 text-sm"
              />
              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="secondary" onClick={() => setEditingUser(null)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={updateMutation.isPending}>
                  {updateMutation.isPending ? 'Saving…' : 'Save changes'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
