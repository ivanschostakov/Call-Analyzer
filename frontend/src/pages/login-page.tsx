import { useEffect, useMemo } from 'react';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link, Navigate, useNavigate } from '@tanstack/react-router';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { useLoginAuthLoginPost, useRegisterAuthRegisterPost } from '../api/generated/client';
import { useAuth } from '../auth/context';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { useViewport } from '../hooks/use-viewport';
import { getErrorMessage } from '../lib/utils';
import { useTheme } from '../theme/theme';
import { getAuthPageStyles } from './auth-page.styles';

const loginSchema = z.object({
  email: z.string().email('Введите корректный email.'),
  password: z.string().min(8, 'Пароль должен быть не короче 8 символов.'),
});

const registerSchema = loginSchema.extend({
  name: z.string().min(1, 'Введите имя.'),
  surname: z.string().min(1, 'Введите фамилию.'),
});

type LoginValues = z.infer<typeof loginSchema>;
type RegisterValues = z.infer<typeof registerSchema>;

function useInvitationContext() {
  return useMemo(() => {
    if (typeof window === 'undefined') {
      return { token: '', email: '', companyName: '', search: '' };
    }

    const params = new URLSearchParams(window.location.search);
    return {
      token: params.get('inviteToken') ?? '',
      email: params.get('inviteEmail') ?? '',
      companyName: params.get('companyName') ?? '',
      search: window.location.search,
    };
  }, []);
}

function AuthShell({
  title,
  description,
  children,
  footer,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
  footer: React.ReactNode;
}) {
  const { tokens } = useTheme();
  const viewport = useViewport();
  const styles = getAuthPageStyles(tokens, { compact: viewport.isCompactNav, mobile: viewport.isMobile });

  return (
    <div style={styles.shell}>
      <div style={styles.container}>
        <section style={styles.intro}>
          <div>
            <p style={styles.introEyebrow}>Call Analyzer</p>
            <h1 style={styles.introTitle}>Контроль звонков без лишнего визуального шума.</h1>
          </div>
          <p style={styles.introBody}>
            Открывайте загрузки, расшифровки и анализы из одной спокойной панели. Новая версия интерфейса стала легче, чище и поддерживает светлую и темную темы.
          </p>
        </section>

        <section style={styles.formCard}>
          <p style={styles.formEyebrow}>Вход в продукт</p>
          <h2 style={styles.formTitle}>{title}</h2>
          <p style={styles.formDescription}>{description}</p>
          <div style={{ marginTop: 8 }}>{children}</div>
          <div style={styles.footer}>{footer}</div>
        </section>
      </div>
    </div>
  );
}

function FieldError({ message }: { message?: string }) {
  const { tokens } = useTheme();

  if (!message) {
    return null;
  }

  return (
    <p
      style={{
        margin: '8px 0 0',
        fontSize: 12,
        lineHeight: 1.5,
        color: tokens.danger,
      }}
    >
      {message}
    </p>
  );
}

export function LoginPage() {
  const auth = useAuth();
  const navigate = useNavigate();
  const mutation = useLoginAuthLoginPost();
  const { tokens } = useTheme();
  const viewport = useViewport();
  const styles = getAuthPageStyles(tokens, { compact: viewport.isCompactNav, mobile: viewport.isMobile });
  const invitation = useInvitationContext();
  const form = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: invitation.email,
      password: '',
    },
  });

  useEffect(() => {
    if (invitation.email) {
      form.setValue('email', invitation.email);
    }
  }, [form, invitation.email]);

  if (auth.isAuthenticated) {
    return <Navigate to="/" />;
  }

  async function onSubmit(values: LoginValues) {
    const response = await mutation.mutateAsync({
      data: {
        ...values,
        invitation_token: invitation.token || undefined,
      },
    });
    auth.setSessionFromResponse(response);
    await navigate({ to: '/' });
  }

  return (
    <AuthShell
      title="Войти"
      description="Используйте email и пароль, чтобы открыть операционную панель."
      footer={
        <>
          Нет аккаунта?{' '}
          {invitation.search ? (
            <a href={`/register${invitation.search}`} style={styles.link}>
              Зарегистрироваться
            </a>
          ) : (
            <Link to="/register" style={styles.link}>
              Зарегистрироваться
            </Link>
          )}
        </>
      }
    >
      <form onSubmit={form.handleSubmit(onSubmit)} style={styles.form}>
        {invitation.token ? (
          <p style={styles.formDescription}>
            Приглашение в компанию{invitation.companyName ? ` ${invitation.companyName}` : ''}. Войдите в аккаунт, чтобы принять его автоматически.
          </p>
        ) : null}
        <div>
          <Label htmlFor="login-email">Email</Label>
          <Input id="login-email" type="email" placeholder="name@company.com" {...form.register('email')} />
          <FieldError message={form.formState.errors.email?.message} />
        </div>

        <div>
          <Label htmlFor="login-password">Пароль</Label>
          <Input id="login-password" type="password" placeholder="Минимум 8 символов" {...form.register('password')} />
          <FieldError message={form.formState.errors.password?.message} />
        </div>

        {mutation.isError ? <p style={styles.error}>{getErrorMessage(mutation.error)}</p> : null}

        <Button type="submit" style={{ width: '100%' }} size="lg" disabled={mutation.isPending}>
          {mutation.isPending ? 'Входим...' : 'Открыть панель'}
        </Button>
      </form>
    </AuthShell>
  );
}

export function RegisterPage() {
  const auth = useAuth();
  const navigate = useNavigate();
  const mutation = useRegisterAuthRegisterPost();
  const { tokens } = useTheme();
  const viewport = useViewport();
  const styles = getAuthPageStyles(tokens, { compact: viewport.isCompactNav, mobile: viewport.isMobile });
  const invitation = useInvitationContext();
  const form = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      email: invitation.email,
      password: '',
      name: '',
      surname: '',
    },
  });

  useEffect(() => {
    if (invitation.email) {
      form.setValue('email', invitation.email);
    }
  }, [form, invitation.email]);

  if (auth.isAuthenticated) {
    return <Navigate to="/" />;
  }

  async function onSubmit(values: RegisterValues) {
    const response = await mutation.mutateAsync({
      data: {
        ...values,
        invitation_token: invitation.token || undefined,
      },
    });
    auth.setSessionFromResponse(response);
    await navigate({ to: '/' });
  }

  return (
    <AuthShell
      title="Регистрация"
      description="Создайте первый аккаунт, чтобы собрать компании, расшифровки и аналитику в одной панели."
      footer={
        <>
          Уже зарегистрированы?{' '}
          {invitation.search ? (
            <a href={`/login${invitation.search}`} style={styles.link}>
              Войти
            </a>
          ) : (
            <Link to="/login" style={styles.link}>
              Войти
            </Link>
          )}
        </>
      }
    >
      <form onSubmit={form.handleSubmit(onSubmit)} style={styles.form}>
        {invitation.token ? (
          <p style={styles.formDescription}>
            Приглашение в компанию{invitation.companyName ? ` ${invitation.companyName}` : ''}. После регистрации вы автоматически попадете в нее как сотрудник.
          </p>
        ) : null}
        <div style={styles.row}>
          <div>
            <Label htmlFor="register-name">Имя</Label>
            <Input id="register-name" placeholder="Иван" {...form.register('name')} />
            <FieldError message={form.formState.errors.name?.message} />
          </div>

          <div>
            <Label htmlFor="register-surname">Фамилия</Label>
            <Input id="register-surname" placeholder="Иванов" {...form.register('surname')} />
            <FieldError message={form.formState.errors.surname?.message} />
          </div>
        </div>

        <div>
          <Label htmlFor="register-email">Email</Label>
          <Input id="register-email" type="email" placeholder="name@company.com" {...form.register('email')} />
          <FieldError message={form.formState.errors.email?.message} />
        </div>

        <div>
          <Label htmlFor="register-password">Пароль</Label>
          <Input id="register-password" type="password" placeholder="Минимум 8 символов" {...form.register('password')} />
          <FieldError message={form.formState.errors.password?.message} />
        </div>

        {mutation.isError ? <p style={styles.error}>{getErrorMessage(mutation.error)}</p> : null}

        <Button type="submit" style={{ width: '100%' }} size="lg" disabled={mutation.isPending}>
          {mutation.isPending ? 'Создаем аккаунт...' : 'Создать аккаунт'}
        </Button>
      </form>
    </AuthShell>
  );
}
