import React, { useState, ChangeEvent } from 'react'
import axios from 'axios'

interface Metadata {
    filename: string
    size: number
    content_type: string
    [key: string]: any
}

const FileUpload: React.FC = () => {
    const [file, setFile] = useState<File | null>(null)
    const [metadata, setMetadata] = useState<Metadata | null>(null)
    const [loading, setLoading] = useState<boolean>(false)

    const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
        if (e.target.files?.length) {
            setFile(e.target.files[0])
            setMetadata(null)
        }
    }

    const handleUpload = async () => {
        if (!file) return

        const formData = new FormData()
        formData.append('file', file)

        setLoading(true)
        try {
            const response = await axios.post<Metadata>('http://localhost:8000/api/upload/', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            })
            setMetadata(response.data)
        } catch (error) {
            console.error('Upload failed:', error)
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="max-w-4xl mx-auto p-6">
            <h2 className="text-2xl font-bold mb-6">Upload a Policy Document</h2>
            <div className="bg-white p-6 rounded shadow-md">
                <input
                    type="file"
                    onChange={handleFileChange}
                    className="mb-4 block w-full text-sm text-gray-700 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                />
                <button
                    onClick={handleUpload}
                    disabled={!file || loading}
                    className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
                >
                    {loading ? 'Uploading...' : 'Upload'}
                </button>
            </div>

            {metadata && (
                <div className="mt-8 bg-gray-100 p-6 rounded shadow">
                    <h3 className="text-lg font-semibold mb-2">Extracted Metadata</h3>
                    <pre className="text-sm whitespace-pre-wrap">{JSON.stringify(metadata, null, 2)}</pre>
                </div>
            )}
        </div>
    )
}

export default FileUpload