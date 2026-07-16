import type { IOCRecord } from '../types/otx'

type Props = {
  iocs: IOCRecord[]
}

export function IocTable({ iocs }: Props) {
  return (
    <div className="overflow-x-auto rounded-lg border border-[#2A2A2A]">
      <table className="min-w-full text-left text-sm">
        <thead className="bg-[#131313] text-neutral-400">
          <tr>
            <th className="px-3 py-2">Type</th>
            <th className="px-3 py-2">Value</th>
            <th className="px-3 py-2">Description</th>
            <th className="px-3 py-2">Pulse</th>
          </tr>
        </thead>
        <tbody>
          {iocs.map((ioc, idx) => (
            <tr key={`${ioc.value}-${idx}`} className="border-t border-[#2A2A2A]">
              <td className="px-3 py-2">{ioc.type}</td>
              <td className="px-3 py-2">{ioc.value}</td>
              <td className="px-3 py-2">{ioc.description || '-'}</td>
              <td className="px-3 py-2">{ioc.pulse_name || '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
