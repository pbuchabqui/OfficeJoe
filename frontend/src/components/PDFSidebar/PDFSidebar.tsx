/**
 * Painel lateral do visualizador PDF.
 * Exibe: número da página, classificação, status de validação,
 * texto OCR, alerta de baixa confiança e item do inventário.
 */

import React from 'react';
import {
  FileText,
  Tag,
  CheckCircle,
  AlertTriangle,
  AlignLeft,
  List,
  Loader,
  XCircle,
  Clock,
} from 'lucide-react';
import { PDFSidebarProps, ValidationStatusValue } from '../../types/sidebar';
import styles from './PDFSidebar.module.css';

// ── sub-componentes ───────────────────────────────────────────────────────────

function SectionHeader({ icon, title }: { icon: React.ReactNode; title: string }) {
  return (
    <div className={styles.sectionHeader}>
      {icon}
      <span>{title}</span>
    </div>
  );
}

function ValidationBadge({ status }: { status: ValidationStatusValue }) {
  const config = {
    validated: { label: 'Validado', className: styles.badgeValidated, Icon: CheckCircle },
    not_validated: { label: 'Não validado', className: styles.badgePending, Icon: Clock },
    rejected: { label: 'Rejeitado', className: styles.badgeRejected, Icon: XCircle },
  };
  const { label, className, Icon } = config[status];
  return (
    <span className={`${styles.badge} ${className}`}>
      <Icon size={12} />
      {label}
    </span>
  );
}

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const colorClass = pct >= 90 ? styles.barHigh : pct >= 70 ? styles.barMid : styles.barLow;
  return (
    <div className={styles.confidenceWrap}>
      <div className={styles.barTrack}>
        <div className={`${styles.barFill} ${colorClass}`} style={{ width: `${pct}%` }} />
      </div>
      <span className={styles.confidenceLabel}>{pct}%</span>
    </div>
  );
}

// ── componente principal ──────────────────────────────────────────────────────

export const PDFSidebar: React.FC<PDFSidebarProps> = ({
  data,
  currentPage,
  loading = false,
  className,
}) => {
  if (loading) {
    return (
      <aside className={`${styles.sidebar} ${className ?? ''}`}>
        <div className={styles.loadingState}>
          <Loader size={24} className={styles.spinner} />
          <p>Carregando dados da página…</p>
        </div>
      </aside>
    );
  }

  return (
    <aside className={`${styles.sidebar} ${className ?? ''}`} aria-label="Painel lateral da página">

      {/* ── Número da página ─────────────────────────────────────────────── */}
      <section className={styles.section} aria-labelledby="section-page">
        <SectionHeader icon={<FileText size={16} />} title="Página" />
        <p id="section-page" className={styles.pageNumber}>
          {currentPage}
        </p>
      </section>

      {/* ── Classificação ────────────────────────────────────────────────── */}
      <section className={styles.section} aria-labelledby="section-class">
        <SectionHeader icon={<Tag size={16} />} title="Classificação" />
        {data?.classification ? (
          <div>
            <p id="section-class" className={styles.classLabel}>
              {data.classification.documentClass}
            </p>
            <ConfidenceBar value={data.classification.confidence} />
            <p className={styles.meta}>
              {data.classification.provider} · {data.classification.modelName}
            </p>
          </div>
        ) : (
          <p id="section-class" className={styles.empty}>Sem classificação</p>
        )}
      </section>

      {/* ── Status de validação ──────────────────────────────────────────── */}
      <section className={styles.section} aria-labelledby="section-validation">
        <SectionHeader icon={<CheckCircle size={16} />} title="Validação" />
        {data ? (
          <div id="section-validation">
            <ValidationBadge status={data.validation.status} />
            {data.validation.validatedBy && (
              <p className={styles.meta}>
                {data.validation.validatedBy}
                {data.validation.validatedAt &&
                  ` · ${new Date(data.validation.validatedAt).toLocaleDateString('pt-BR')}`}
              </p>
            )}
          </div>
        ) : (
          <p id="section-validation" className={styles.empty}>Sem dados</p>
        )}
      </section>

      {/* ── Texto OCR ────────────────────────────────────────────────────── */}
      <section className={styles.section} aria-labelledby="section-ocr">
        <SectionHeader icon={<AlignLeft size={16} />} title="Texto OCR" />
        {data?.ocr ? (
          <div id="section-ocr">
            {data.ocr.hasLowConfidence && (
              <div className={styles.lowConfidenceAlert} role="alert">
                <AlertTriangle size={14} />
                <span>Trechos com baixa confiança</span>
              </div>
            )}
            {data.ocr.averageConfidence !== null && (
              <div className={styles.ocrConfidence}>
                <span className={styles.metaLabel}>Confiança média</span>
                <ConfidenceBar value={data.ocr.averageConfidence} />
              </div>
            )}
            <div className={styles.ocrText} aria-label="Texto extraído por OCR">
              {data.ocr.blocks.map((block, i) => (
                <span
                  key={i}
                  className={block.lowConfidence ? styles.lowConfidenceText : undefined}
                  title={block.lowConfidence ? `Confiança: ${Math.round(block.confidence * 100)}%` : undefined}
                >
                  {block.text}{' '}
                </span>
              ))}
            </div>
          </div>
        ) : (
          <p id="section-ocr" className={styles.empty}>Sem texto OCR</p>
        )}
      </section>

      {/* ── Item do inventário ───────────────────────────────────────────── */}
      <section className={styles.section} aria-labelledby="section-inventory">
        <SectionHeader icon={<List size={16} />} title="Inventário" />
        {data?.inventoryItem ? (
          <div id="section-inventory" className={styles.inventoryCard}>
            <p className={styles.classLabel}>
              {data.inventoryItem.customLabel ?? data.inventoryItem.documentClass}
            </p>
            <p className={styles.meta}>
              Págs. {data.inventoryItem.startPage}–{data.inventoryItem.endPage}
              {' '}({data.inventoryItem.pageCount} páginas)
            </p>
            {!data.inventoryItem.isRelevant && (
              <span className={`${styles.badge} ${styles.badgePending}`}>
                Não relevante
              </span>
            )}
          </div>
        ) : (
          <p id="section-inventory" className={styles.empty}>Sem item de inventário</p>
        )}
      </section>

    </aside>
  );
};

export default PDFSidebar;
