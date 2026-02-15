import MarketOverlay from './MarketOverlay.jsx'

export default function ShopOverlay(props) {
  const id = props.buildingId ?? '-'
  return (
    <MarketOverlay
      {...props}
      titleName={`Petshop #${id}`}
      titleType="ЗООМАГАЗИН"
      stripName={`Petshop #${id}`}
      stripType="ЗООМАГАЗИН"
      overlayType="shop"
    />
  )
}
