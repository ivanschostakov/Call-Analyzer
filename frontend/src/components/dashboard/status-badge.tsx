import type { TranscriptionStatus } from '../../api/generated/model';
import { Badge } from '../ui/badge';

const labelByStatus: Record<TranscriptionStatus, string> = {
  uploaded: 'Загружен',
  queued: 'В очереди',
  processing: 'В обработке',
  completed: 'Готово',
  failed: 'Ошибка',
};

const toneByStatus: Record<TranscriptionStatus, 'default' | 'success' | 'warning' | 'danger'> = {
  uploaded: 'default',
  queued: 'warning',
  processing: 'warning',
  completed: 'success',
  failed: 'danger',
};

export function StatusBadge({ status }: { status: TranscriptionStatus }) {
  return <Badge tone={toneByStatus[status]}>{labelByStatus[status]}</Badge>;
}
