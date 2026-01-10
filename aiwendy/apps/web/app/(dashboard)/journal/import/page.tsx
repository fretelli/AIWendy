'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { Upload, ArrowLeft } from 'lucide-react';

import { useI18n } from '@/lib/i18n/provider';
import { journalApi } from '@/lib/api/journal';
import { useActiveProjectId } from '@/lib/active-project';
import type { JournalImportPreviewResponse, JournalImportResponse } from '@/lib/types/journal';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useToast } from '@/hooks/use-toast';

type Mapping = Record<string, string>;

const NONE = '__none__';

export default function JournalImportPage() {
  const { toast } = useToast();
  const { t, locale } = useI18n();
  const { projectId } = useActiveProjectId();

  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<JournalImportPreviewResponse | null>(null);
  const [mapping, setMapping] = useState<Mapping>({});
  const [strict, setStrict] = useState(false);
  const [dryRun, setDryRun] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<JournalImportResponse | null>(null);

  const fields = useMemo(
    () => [
      { key: 'symbol', label: t('journal.symbol'), required: true },
      { key: 'direction', label: t('journal.side'), required: true },
      { key: 'trade_date', label: locale === 'zh' ? '日期/时间' : 'Date/Time', required: false },
      { key: 'entry_price', label: t('journal.entryPrice'), required: false },
      { key: 'exit_price', label: t('journal.exitPrice'), required: false },
      { key: 'position_size', label: t('journal.quantity'), required: false },
      { key: 'pnl_amount', label: t('journal.pnl'), required: false },
      { key: 'notes', label: t('journal.notes'), required: false },
    ],
    [locale, t]
  );

  const requiredOk = useMemo(() => {
    return fields.filter(f => f.required).every(f => Boolean(mapping[f.key]));
  }, [fields, mapping]);

  const onPickFile = async (nextFile: File | null) => {
    setFile(nextFile);
    setResult(null);
    setPreview(null);
    setMapping({});

    if (!nextFile) return;

    setIsLoading(true);
    try {
      const nextPreview = await journalApi.importPreview(nextFile, 20);
      setPreview(nextPreview);

      const suggested: Mapping = {};
      Object.entries(nextPreview.suggested_mapping || {}).forEach(([k, v]) => {
        if (v) suggested[k] = v;
      });
      setMapping(suggested);
    } catch (e) {
      toast({
        title: t('common.error'),
        description: e instanceof Error ? e.message : String(e),
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const onImport = async () => {
    if (!file || !preview) return;
    if (!requiredOk) {
      toast({
        title: t('common.error'),
        description: locale === 'zh' ? '请先完成必填字段映射（标的、方向）。' : 'Map required fields (symbol, side) first.',
        variant: 'destructive',
      });
      return;
    }

    setIsLoading(true);
    try {
      const res = await journalApi.importTrades({
        file,
        mapping,
        project_id: projectId,
        strict,
        dry_run: dryRun,
      });
      setResult(res);
      toast({
        title: t('common.success'),
        description:
          locale === 'zh'
            ? `导入完成：新增 ${res.created}，跳过 ${res.skipped}`
            : `Imported: created ${res.created}, skipped ${res.skipped}`,
      });
    } catch (e) {
      toast({
        title: t('common.error'),
        description: e instanceof Error ? e.message : String(e),
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="container mx-auto max-w-5xl px-4 py-10 space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link href="/journal">
            <Button variant="ghost">
              <ArrowLeft className="mr-2 h-4 w-4" />
              {t('common.back')}
            </Button>
          </Link>
          <h1 className="text-3xl font-bold">{t('journal.import')}</h1>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{locale === 'zh' ? '上传文件' : 'Upload file'}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col gap-2">
            <Input
              type="file"
              accept=".csv,.xlsx"
              disabled={isLoading}
              onChange={(e) => onPickFile(e.target.files?.[0] ?? null)}
            />
            <p className="text-sm text-muted-foreground">
              {locale === 'zh'
                ? '支持 CSV / XLSX。不同券商/平台格式可通过下方“列映射”适配。'
                : 'CSV/XLSX supported. Use column mapping below for different broker formats.'}
            </p>
          </div>

          <div className="flex items-center gap-6">
            <label className="flex items-center gap-2 text-sm">
              <Checkbox checked={strict} onCheckedChange={(v) => setStrict(Boolean(v))} />
              {locale === 'zh' ? '遇到错误立即停止（严格模式）' : 'Stop on first error (strict)'}
            </label>
            <label className="flex items-center gap-2 text-sm">
              <Checkbox checked={dryRun} onCheckedChange={(v) => setDryRun(Boolean(v))} />
              {locale === 'zh' ? '仅校验（不写入数据库）' : 'Dry-run (validate only)'}
            </label>
          </div>

          {preview?.warnings?.length ? (
            <div className="rounded-md border p-3 text-sm text-muted-foreground space-y-1">
              {preview.warnings.map((w, i) => (
                <div key={i}>{w}</div>
              ))}
            </div>
          ) : null}
        </CardContent>
      </Card>

      {preview ? (
        <Card>
          <CardHeader>
            <CardTitle>{locale === 'zh' ? '列映射' : 'Column mapping'}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {fields.map((field) => (
                <div key={field.key} className="space-y-2">
                  <div className="text-sm font-medium">
                    {field.label}
                    {field.required ? <span className="text-red-500"> *</span> : null}
                  </div>
                  <Select
                    value={mapping[field.key] ?? NONE}
                    onValueChange={(value) => {
                      setMapping((prev) => {
                        const next = { ...prev };
                        if (value === NONE) delete next[field.key];
                        else next[field.key] = value;
                        return next;
                      });
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder={locale === 'zh' ? '选择列' : 'Select column'} />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value={NONE}>{locale === 'zh' ? '不导入' : 'Skip'}</SelectItem>
                      {preview.columns.map((col) => (
                        <SelectItem key={col} value={col}>
                          {col}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              ))}
            </div>

            <div className="flex justify-end">
              <Button onClick={onImport} disabled={isLoading || !requiredOk}>
                <Upload className="mr-2 h-4 w-4" />
                {dryRun ? (locale === 'zh' ? '校验' : 'Validate') : (locale === 'zh' ? '开始导入' : 'Import')}
              </Button>
            </div>

            {result ? (
              <div className="rounded-md border p-3 text-sm space-y-2">
                <div>
                  {locale === 'zh'
                    ? `结果：新增 ${result.created}，跳过 ${result.skipped}`
                    : `Result: created ${result.created}, skipped ${result.skipped}`}
                </div>
                {!dryRun ? (
                  <div>
                    <Link href="/journal" className="underline">
                      {locale === 'zh' ? '查看交易日志' : 'View journal'}
                    </Link>
                  </div>
                ) : null}
                {result.errors?.length ? (
                  <div className="text-muted-foreground space-y-1">
                    {result.errors.slice(0, 10).map((err, i) => (
                      <div key={i}>{err}</div>
                    ))}
                  </div>
                ) : null}
              </div>
            ) : null}
          </CardContent>
        </Card>
      ) : null}

      {preview?.sample_rows?.length ? (
        <Card>
          <CardHeader>
            <CardTitle>{locale === 'zh' ? '预览（前几行）' : 'Preview (first rows)'}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="rounded-md border overflow-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    {preview.columns.slice(0, 8).map((col) => (
                      <TableHead key={col}>{col}</TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {preview.sample_rows.slice(0, 10).map((row, idx) => (
                    <TableRow key={idx}>
                      {preview.columns.slice(0, 8).map((col) => (
                        <TableCell key={col} className="max-w-[220px] truncate">
                          {row[col] ?? ''}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
