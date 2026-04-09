import MarketOverlay from './MarketOverlay.jsx'

export default function CatteryOverlay(props) {
  const id = props.buildingId ?? '-'
  const name = props.buildingName || `Питомник #${id}`
  return (
    <MarketOverlay
      {...props}
      titleName={name}
      titleType="ПИТОМНИК"
      stripName={name}
      stripType="ПИТОМНИК"
      overlayType="cattery"
    />
  )
}
