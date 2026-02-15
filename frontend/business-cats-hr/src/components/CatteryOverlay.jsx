import MarketOverlay from './MarketOverlay.jsx'

export default function CatteryOverlay(props) {
  const id = props.buildingId ?? '-'
  return (
    <MarketOverlay
      {...props}
      titleName={`Cattery #${id}`}
      titleType="ПИТОМНИК"
      stripName={`Cattery #${id}`}
      stripType="ПИТОМНИК"
      overlayType="cattery"
    />
  )
}
