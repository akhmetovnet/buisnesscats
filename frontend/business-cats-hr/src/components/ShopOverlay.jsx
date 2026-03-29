import MarketOverlay from './MarketOverlay.jsx'

export default function ShopOverlay(props) {
  const id = props.buildingId ?? '-'
  const name = props.buildingName || `Зоомагазин #${id}`
  return (
    <MarketOverlay
      {...props}
      titleName={name}
      titleType="ЗООМАГАЗИН"
      stripName={name}
      stripType="ЗООМАГАЗИН"
      overlayType="shop"
    />
  )
}
