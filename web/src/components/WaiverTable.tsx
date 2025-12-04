import React, { useEffect, useState } from 'react'
import axios from 'axios'

interface WaiverDocument {
  id: number
  file: string
  state: string
  program_title: string
  proposed_effective_date: string
  approved_effective_date: string
  amended_effective_date: string
  application_type: string
  application_number: string
}

const WaiverTable: React.FC = () => {
  const [documents, setDocuments] = useState<WaiverDocument[]>([])

  useEffect(() => {
    axios.get<WaiverDocument[]>('http://localhost:8000/api/documents/')
      .then(res => setDocuments(res.data))
      .catch(err => console.error(err))
  }, [])

  return (
    <div className="max-w-6xl mx-auto p-6">
      <h2 className="text-2xl font-bold mb-4">Uploaded Waiver Documents</h2>
      <table className="table-auto w-full border-collapse border border-gray-300">
        <thead className="bg-gray-100">
          <tr>
            <th className="border px-4 py-2">Application #</th>
            <th className="border px-4 py-2">State</th>
            <th className="border px-4 py-2">Program Title</th>
            <th className="border px-4 py-2">Proposed Effective Date</th>
            <th className="border px-4 py-2">Approved Effective Date</th>
            <th className="border px-4 py-2">Approved Effective Date of Waiver being Amended</th>
            <th className="border px-4 py-2">Type</th>
            <th className="border px-4 py-2">Preview</th>
          </tr>
        </thead>
        <tbody>
          {documents.map(doc => (
            <tr key={doc.id}>
              <td className="border px-4 py-2">{doc.application_number}</td>
              <td className="border px-4 py-2">{doc.state}</td>
              <td className="border px-4 py-2">{doc.program_title}</td>
              <td className="border px-4 py-2">{doc.proposed_effective_date}</td>
              <td className="border px-4 py-2">{doc.approved_effective_date}</td>
              <td className="border px-4 py-2">{doc.amended_effective_date}</td>
              <td className="border px-4 py-2">{doc.application_type}</td>
              <td className="border px-4 py-2">
                <a
                  href={`http://localhost:8000/media/${doc.file}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline"
                >
                  View PDF
                </a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default WaiverTable