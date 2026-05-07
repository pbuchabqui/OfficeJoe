/**
 * Exemplo de integração: PDFViewer + PDFSidebar lado a lado.
 * Os dados do painel vêm do hook useSidebarData (mockado).
 * Em produção, useSidebarData seria substituído por chamadas à API.
 */

import React, { useState } from 'react';
import { PDFViewer } from './PDFViewer';
import { PDFSidebar } from '../PDFSidebar/PDFSidebar';
import { useSidebarData } from '../../hooks/useSidebarData';
import styles from './PDFViewerContainer.module.css';

interface PDFViewerContainerProps {
  url: string;
  height?: string;
  className?: string;
}

export const PDFViewerContainer: React.FC<PDFViewerContainerProps> = ({
  url,
  height = '700px',
  className,
}) => {
  const [currentPage, setCurrentPage] = useState(1);
  const { data } = useSidebarData(currentPage);

  return (
    <div
      className={`${styles.container} ${className ?? ''}`}
      style={{ height }}
    >
      <div className={styles.viewer}>
        <PDFViewer
          url={url}
          height="100%"
          onPageChange={setCurrentPage}
        />
      </div>
      <PDFSidebar
        data={data}
        currentPage={currentPage}
        className={styles.sidebar}
      />
    </div>
  );
};

export default PDFViewerContainer;
