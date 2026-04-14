import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { useCreateCompanyRouteCompaniesPost } from '../../api/generated/client';
import { getErrorMessage } from '../../lib/utils';
import { useTheme } from '../../theme/theme';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';

const schema = z.object({
  name: z.string().min(1, 'Введите название компании.'),
  description: z.string().max(500, 'Описание слишком длинное.').optional(),
});

type Values = z.infer<typeof schema>;

export function CreateCompanyForm({ onCreated }: { onCreated: () => void }) {
  const { tokens } = useTheme();
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: '',
      description: '',
    },
  });

  const mutation = useCreateCompanyRouteCompaniesPost();

  async function onSubmit(values: Values) {
    await mutation.mutateAsync({
      data: {
        name: values.name,
        description: values.description || null,
      },
    });
    form.reset();
    onCreated();
  }

  return (
    <form
      onSubmit={form.handleSubmit(onSubmit)}
      style={{
        display: 'grid',
        gap: 16,
        gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
      }}
    >
      <div>
        <Label htmlFor="company-name">Название компании</Label>
        <Input id="company-name" placeholder="Например, Sales Team East" {...form.register('name')} />
        {form.formState.errors.name ? (
          <p
            style={{
              margin: '8px 0 0',
              fontSize: 12,
              color: tokens.danger,
            }}
          >
            {form.formState.errors.name.message}
          </p>
        ) : null}
      </div>

      <div>
        <Label htmlFor="company-description">Описание</Label>
        <Input id="company-description" placeholder="Необязательно" {...form.register('description')} />
        {form.formState.errors.description ? (
          <p
            style={{
              margin: '8px 0 0',
              fontSize: 12,
              color: tokens.danger,
            }}
          >
            {form.formState.errors.description.message}
          </p>
        ) : null}
      </div>

      <div
        style={{
          display: 'flex',
          alignItems: 'flex-end',
        }}
      >
        <Button type="submit" style={{ width: '100%' }} disabled={mutation.isPending}>
          {mutation.isPending ? 'Создаю...' : 'Создать компанию'}
        </Button>
      </div>

      {mutation.isError ? (
        <p
          style={{
            margin: 0,
            fontSize: 14,
            color: tokens.danger,
            gridColumn: '1 / -1',
          }}
        >
          {getErrorMessage(mutation.error)}
        </p>
      ) : null}
    </form>
  );
}
