import { useMemo, useState } from 'react';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link } from '@tanstack/react-router';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { confirmPasswordReset, requestPasswordReset } from '../api/password-reset';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { getErrorMessage } from '../lib/utils';
import { useTheme } from '../theme/theme';
import { AuthShell, FieldError } from './login-page';

const requestSchema = z.object({
  email: z.string().email('Введите корректный email.'),
});

const confirmSchema = z
  .object({
    password: z.string().min(8, 'Пароль должен быть не короче 8 символов.'),
    passwordConfirmation: z.string(),
  })
  .refine((values) => values.password === values.passwordConfirmation, {
    message: 'Пароли не совпадают.',
    path: ['passwordConfirmation'],
  });

type RequestValues = z.infer<typeof requestSchema>;
type ConfirmValues = z.infer<typeof confirmSchema>;

export function PasswordResetPage() {
  const token = useMemo(() => {
    if (typeof window === 'undefined') {
      return '';
    }
    return new URLSearchParams(window.location.search).get('token') ?? '';
  }, []);

  return token ? <ConfirmPasswordForm token={token} /> : <RequestPasswordForm />;
}

function RequestPasswordForm() {
  const { tokens } = useTheme();
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPending, setIsPending] = useState(false);
  const form = useForm<RequestValues>({
    resolver: zodResolver(requestSchema),
    defaultValues: { email: '' },
  });

  async function onSubmit(values: RequestValues) {
    try {
      setIsPending(true);
      setError(null);
      const response = await requestPasswordReset(values.email);
      setMessage(response.message);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setIsPending(false);
    }
  }

  return (
    <AuthShell
      title="Восстановить пароль"
      description="Укажите email аккаунта. Мы отправим одноразовую ссылку для смены пароля."
      footer={<Link to="/login">Вернуться ко входу</Link>}
    >
      {message ? (
        <p style={{ margin: 0, color: tokens.success, lineHeight: 1.6 }}>{message}</p>
      ) : (
        <form onSubmit={form.handleSubmit(onSubmit)} style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          <div>
            <Label htmlFor="reset-email">Email</Label>
            <Input id="reset-email" type="email" placeholder="name@company.com" {...form.register('email')} />
            <FieldError message={form.formState.errors.email?.message} />
          </div>
          {error ? <p style={{ margin: 0, color: tokens.danger }}>{error}</p> : null}
          <Button type="submit" size="lg" disabled={isPending}>
            {isPending ? 'Отправляем...' : 'Отправить ссылку'}
          </Button>
        </form>
      )}
    </AuthShell>
  );
}

function ConfirmPasswordForm({ token }: { token: string }) {
  const { tokens } = useTheme();
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPending, setIsPending] = useState(false);
  const form = useForm<ConfirmValues>({
    resolver: zodResolver(confirmSchema),
    defaultValues: { password: '', passwordConfirmation: '' },
  });

  async function onSubmit(values: ConfirmValues) {
    try {
      setIsPending(true);
      setError(null);
      const response = await confirmPasswordReset(token, values.password);
      setMessage(response.message);
    } catch (confirmError) {
      setError(getErrorMessage(confirmError));
    } finally {
      setIsPending(false);
    }
  }

  return (
    <AuthShell
      title="Новый пароль"
      description="Задайте новый пароль для входа в Call Analyzer."
      footer={<Link to="/login">Вернуться ко входу</Link>}
    >
      {message ? (
        <p style={{ margin: 0, color: tokens.success, lineHeight: 1.6 }}>{message}</p>
      ) : (
        <form onSubmit={form.handleSubmit(onSubmit)} style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          <div>
            <Label htmlFor="reset-password">Новый пароль</Label>
            <Input id="reset-password" type="password" placeholder="Минимум 8 символов" {...form.register('password')} />
            <FieldError message={form.formState.errors.password?.message} />
          </div>
          <div>
            <Label htmlFor="reset-password-confirmation">Повторите пароль</Label>
            <Input id="reset-password-confirmation" type="password" {...form.register('passwordConfirmation')} />
            <FieldError message={form.formState.errors.passwordConfirmation?.message} />
          </div>
          {error ? <p style={{ margin: 0, color: tokens.danger }}>{error}</p> : null}
          <Button type="submit" size="lg" disabled={isPending}>
            {isPending ? 'Сохраняем...' : 'Сохранить пароль'}
          </Button>
        </form>
      )}
    </AuthShell>
  );
}
