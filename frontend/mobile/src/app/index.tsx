import { useEffect, useState } from 'react'

import {
    View,
    Text,
    Button,
    Image,
    ScrollView,
    StyleSheet,
    TextInput,
    Alert,
    Platform,
    Linking,
    AppState
} from 'react-native'

import * as ImagePicker from 'expo-image-picker'
import { fetch } from 'expo/fetch'
import { File } from 'expo-file-system'


const PC_IP = '192.168.0.100'
const API = `http://${PC_IP}:8000`

const CONTRACT_ADDRESS = '0x5FbDB2315678afecb367f032d93F642f64180aa3'

const CHAIN_ID = 31415;

const PACKAGE_PRICE_WEI = '2000000000000000'


type BirdResult = {
    species: string
    confidence: number
}


type AnalyzeResult = {
    id: number
    image_name: string
    best_result: BirdResult
    top_3: BirdResult[]
    credits_left: number
}


type HistoryItem = {
    id: number
    image_name: string
    predicted_species: string
    confidence: number
    analysis_date: string
}


export default function App() {

    const [image, setImage] = useState<ImagePicker.ImagePickerAsset | null>(null)

    const [result, setResult] = useState<AnalyzeResult | null>(null)

    const [history, setHistory] = useState<HistoryItem[]>([])

    const [search, setSearch] = useState('')

    const [stats, setStats] = useState<any>(null)

    const [loading, setLoading] = useState(false)

    const [walletAddress, setWalletAddress] = useState('')

    const [credits, setCredits] = useState(0)

    const [showPayment, setShowPayment] = useState(false)

    const [paymentLoading, setPaymentLoading] = useState(false)

    useEffect(() => {

        const subscription =
            AppState.addEventListener(
                'change',
                async state => {

                    if (
                        state === 'active'
                        &&
                        walletAddress
                    ) {
                        if (showPayment) {
                            await waitForPayment()
                        } else {
                            await refreshCredits()
                        }
                    }
                }
            )

        return () =>
            subscription.remove()

    }, [walletAddress, showPayment])


    async function connectWallet() {

        if (Platform.OS === 'web') {

            try {

                const ethereum =
                    (globalThis as any).ethereum

                if (!ethereum) {

                    Alert.alert(
                        'MetaMask',
                        'Встановіть розширення MetaMask'
                    )

                    return
                }

                const accounts =
                    await ethereum.request({
                        method:
                            'eth_requestAccounts'
                    })

                const account =
                    accounts?.[0]

                if (!account) {
                    return
                }

                setWalletAddress(account)

                await refreshCredits(account)

            } catch (error) {

                Alert.alert(
                    'MetaMask',
                    String(error)
                )
            }

            return
        }


        Alert.alert(
            'MetaMask',
            'Вкажіть адресу вашого MetaMask у полі нижче'
        )
    }


    async function refreshCredits(
        address: string = walletAddress
    ) {

        if (!address) {
            return 0
        }

        try {

            const response =
                await fetch(
                    `${API}/credits/${address}`
                )

            const data =
                await response.json()

            setCredits(
                data.credits
            )

            return data.credits

        } catch (error) {

            console.log(
                'Credits error:',
                error
            )

            return 0
        }
    }


    async function waitForPayment() {

        if (!walletAddress) {
            return
        }

        setPaymentLoading(true)

        try {

            for (
                let i = 0;
                i < 20;
                i++
            ) {

                const response =
                    await fetch(
                        `${API}/payment/check/${walletAddress}`,
                        {
                            method:
                                'POST'
                        }
                    )

                if (response.ok) {

                    const data =
                        await response.json()

                    setCredits(
                        data.credits
                    )

                    setShowPayment(false)

                    return
                }

                await new Promise(
                    resolve =>
                        setTimeout(
                            resolve,
                            1000
                        )
                )
            }

            await refreshCredits()

        } catch (error) {

            console.log(
                'Payment check error:',
                error
            )

        } finally {

            setPaymentLoading(false)
        }
    }



    async function buyPackage() {

        if (!walletAddress.trim()) {

            Alert.alert(
                'MetaMask',
                'Спочатку вкажіть адресу гаманця'
            )

            return
        }


        if (Platform.OS === 'web') {

            try {

                setPaymentLoading(true)

                const ethereum =
                    (globalThis as any).ethereum

                if (!ethereum) {

                    Alert.alert(
                        'MetaMask',
                        'Розширення MetaMask не знайдено'
                    )

                    return
                }

                const chainIdHex =
                    '0x'
                    +
                    CHAIN_ID.toString(16)

                await ethereum.request({
                    method:
                        'wallet_switchEthereumChain',

                    params: [{
                        chainId:
                            chainIdHex
                    }]
                })

                const valueHex =
                    '0x'
                    +
                    BigInt(
                        PACKAGE_PRICE_WEI
                    ).toString(16)

                await ethereum.request({
                    method:
                        'eth_sendTransaction',

                    params: [{
                        from:
                            walletAddress,

                        to:
                            CONTRACT_ADDRESS,

                        value:
                            valueHex
                    }]
                })

                setPaymentLoading(false)

                await waitForPayment()

            } catch (error) {

                setPaymentLoading(false)

                Alert.alert(
                    'Помилка оплати',
                    String(error)
                )
            }

            return
        }


        try {

            setPaymentLoading(true)

            const metamaskUrl =
                `https://link.metamask.io/send/`
                +
                `${CONTRACT_ADDRESS}@${CHAIN_ID}`
                +
                `?value=${PACKAGE_PRICE_WEI}`

            await Linking.openURL(
                metamaskUrl
            )

        } catch (error) {

            setPaymentLoading(false)

            Alert.alert(
                'MetaMask',
                String(error)
            )
        }
    }






    async function selectPhoto() {

        const response =
            await ImagePicker.launchImageLibraryAsync({
                mediaTypes: ['images'],
                quality: 1
            })

        if (!response.canceled) {

            setImage(
                response.assets[0]
            )

            setResult(null)
        }
    }


    async function analyzePhoto() {

        if (!walletAddress.trim()) {

            Alert.alert(
                'MetaMask',
                'Спочатку підключіть або вкажіть гаманець'
            )

            return
        }

        if (!image) {

            Alert.alert(
                'Помилка',
                'Спочатку оберіть фотографію'
            )

            return
        }


        setLoading(true)

        try {

            const formData =
                new FormData()


            if (Platform.OS === 'web') {

                const imageResponse =
                    await globalThis.fetch(
                        image.uri
                    )

                const blob =
                    await imageResponse.blob()

                formData.append(
                    'file',
                    blob,
                    image.fileName || 'bird.jpg'
                )
            }

            else {

                const file =
                    new File(
                        image.uri
                    )

                formData.append(
                    'file',
                    file
                )
            }


            formData.append(
                'wallet_address',
                walletAddress
            )


            const response =
                await fetch(
                    `${API}/analyze`,
                    {
                        method:
                            'POST',

                        body:
                            formData,

                        headers: {
                            Accept:
                                'application/json'
                        }
                    }
                )


            const text =
                await response.text()


            if (response.status === 402) {

                setCredits(0)
                setShowPayment(true)

                return
            }


            if (!response.ok) {

                Alert.alert(
                    'Помилка backend',
                    `${response.status}\n${text}`
                )

                return
            }


            const data:
                AnalyzeResult =
                JSON.parse(text)

            setResult(data)

            setCredits(
                data.credits_left
            )

            setShowPayment(false)

            await loadHistory()

        } catch (error) {

            console.log(
                'Analyze error:',
                error
            )

            Alert.alert(
                'Помилка',
                String(error)
            )

        } finally {

            setLoading(false)
        }
    }


    async function loadHistory() {

        try {

            const response =
                await fetch(
                    `${API}/history`
                )

            const data =
                await response.json()

            setHistory(data)

        } catch {

            Alert.alert(
                'Помилка',
                'Не вдалося завантажити історію'
            )
        }
    }


    async function searchBird() {

        if (!search.trim()) {

            await loadHistory()

            return
        }

        try {

            const response =
                await fetch(
                    `${API}/search?name=${encodeURIComponent(search)}`
                )

            const data =
                await response.json()

            setHistory(data)

        } catch {

            Alert.alert(
                'Помилка',
                'Не вдалося виконати пошук'
            )
        }
    }


    async function deleteBird(
        id: number
    ) {

        try {

            await fetch(
                `${API}/birds/${id}`,
                {
                    method:
                        'DELETE'
                }
            )

            await loadHistory()

        } catch {

            Alert.alert(
                'Помилка',
                'Не вдалося видалити запис'
            )
        }
    }


    async function loadStatistics() {

        try {

            const response =
                await fetch(
                    `${API}/statistics`
                )

            const data =
                await response.json()

            setStats(data)

        } catch {

            Alert.alert(
                'Помилка',
                'Не вдалося отримати статистику'
            )
        }
    }


    async function exportCSV() {

        try {

            const response =
                await fetch(
                    `${API}/export`,
                    {
                        method:
                            'POST'
                    }
                )

            const data = await response.json()

            Alert.alert(
                'CSV',
                `${data.message}\n${data.file}`
            )

        } catch {

            Alert.alert(
                'Помилка',
                'Не вдалося створити CSV'
            )
        }
    }


    return (

        <ScrollView style={styles.page}>

            <Text style={styles.mainTitle}>
                AI BIRD LAB
            </Text>


            <View style={styles.block}>

                <Text style={styles.title}>
                    MetaMask
                </Text>


                {
                    Platform.OS !== 'web' &&

                    <TextInput
                        style={styles.input}
                        placeholder='0x... адреса MetaMask'
                        placeholderTextColor='#777'
                        autoCapitalize='none'
                        autoCorrect={false}
                        value={walletAddress}
                        onChangeText={
                            setWalletAddress
                        }
                    />
                }


                {!walletAddress ? (

                    <Button
                        title={
                            Platform.OS === 'web'
                                ? 'ПІДКЛЮЧИТИ METAMASK'
                                : 'ЯК ПІДКЛЮЧИТИ'
                        }
                        onPress={
                            connectWallet
                        }
                    />

                ) : (

                    <>
                        <Text style={styles.historyText}>
                            {walletAddress.slice(0, 8)}
                            ...
                            {walletAddress.slice(-6)}
                        </Text>

                        <Text style={styles.historyText}>
                            Аналізів: {credits}
                        </Text>

                    </>

                )}

            </View>


            <View style={styles.block}>

                <Text style={styles.title}>
                    Аналіз фотографії
                </Text>

                <Button
                    title='ОБРАТИ ФОТО'
                    onPress={
                        selectPhoto
                    }
                />

                {
                    image &&

                    <Image
                        source={{
                            uri: image.uri
                        }}
                        style={
                            styles.image
                        }
                    />
                }

                <View style={styles.space} />

                <Button
                    title={
                        loading
                            ? 'АНАЛІЗ...'
                            : 'ПРОАНАЛІЗУВАТИ'
                    }
                    onPress={
                        analyzePhoto
                    }
                    disabled={
                        loading
                    }
                />

            </View>


            {
                showPayment && (

                    <View style={styles.resultBlock}>

                        <Text style={styles.resultTitle}>
                            Потрібна оплата
                        </Text>

                        <Text style={styles.resultText}>
                            5 аналізів — 0.002 ETH
                        </Text>

                        <Button
                            title={
                                paymentLoading
                                    ? 'ОЧІКУВАННЯ ОПЛАТИ...'
                                    : 'КУПИТИ 5 АНАЛІЗІВ'
                            }
                            onPress={
                                buyPackage
                            }
                            disabled={
                                paymentLoading
                            }
                        />


                    </View>
                )
            }


            {
                result &&

                <View style={styles.resultBlock}>

                    <Text style={styles.resultTitle}>
                        Результат
                    </Text>

                    <Text style={styles.resultBird}>
                        {result.best_result.species}
                    </Text>

                    <Text style={styles.resultText}>
                        Впевненість:{' '}
                        {
                            (
                                result.best_result.confidence
                                * 100
                            ).toFixed(2)
                        }%
                    </Text>

                    <Text style={styles.resultText}>
                        Залишилось аналізів:{' '}
                        {result.credits_left}
                    </Text>

                    <Text style={styles.resultSubTitle}>
                        TOP 3
                    </Text>

                    {
                        result.top_3.map(
                            (bird, index) => (

                                <Text
                                    key={index}
                                    style={styles.resultText}
                                >
                                    {index + 1}. {bird.species}
                                    {' — '}
                                    {
                                        (
                                            bird.confidence
                                            * 100
                                        ).toFixed(2)
                                    }%
                                </Text>

                            )
                        )
                    }

                </View>
            }


            <View style={styles.block}>

                <Text style={styles.title}>
                    Історія
                </Text>

                <Button
                    title='ПОКАЗАТИ ІСТОРІЮ'
                    onPress={
                        loadHistory
                    }
                />

                <TextInput
                    style={styles.input}
                    placeholder='Назва птаха'
                    placeholderTextColor='#777'
                    value={search}
                    onChangeText={
                        setSearch
                    }
                />

                <Button
                    title='ПОШУК'
                    onPress={
                        searchBird
                    }
                />

                {
                    history.map(
                        item => (

                            <View
                                style={styles.historyItem}
                                key={item.id}
                            >

                                <Text style={styles.historyText}>
                                    {item.id}. {item.predicted_species}
                                </Text>

                                <Text style={styles.historyText}>
                                    {
                                        (
                                            item.confidence
                                            * 100
                                        ).toFixed(2)
                                    }%
                                </Text>

                                <Button
                                    title='ВИДАЛИТИ'
                                    onPress={() =>
                                        deleteBird(item.id)
                                    }
                                />

                            </View>

                        )
                    )
                }

            </View>


            <View style={styles.block}>

                <Text style={styles.title}>
                    Статистика
                </Text>

                <Button
                    title='ПОКАЗАТИ СТАТИСТИКУ'
                    onPress={
                        loadStatistics
                    }
                />

                {
                    stats &&

                    <View style={styles.stats}>

                        <Text style={styles.statsText}>
                            Фото: {stats.total_images}
                        </Text>

                        {
                            stats.most_common_species &&

                            <Text style={styles.statsText}>
                                Найчастіший вид:{' '}
                                {
                                    stats
                                        .most_common_species
                                        .species
                                }
                            </Text>
                        }

                        {
                            stats.highest_confidence &&

                            <Text style={styles.statsText}>
                                Найвища впевненість:{' '}
                                {
                                    (
                                        stats
                                            .highest_confidence
                                            .confidence
                                        * 100
                                    ).toFixed(2)
                                }%
                            </Text>
                        }

                        {
                            stats.lowest_confidence &&

                            <Text style={styles.statsText}>
                                Найнижча впевненість:{' '}
                                {
                                    (
                                        stats
                                            .lowest_confidence
                                            .confidence
                                        * 100
                                    ).toFixed(2)
                                }%
                            </Text>
                        }

                    </View>
                }

            </View>


            <View style={styles.block}>

                <Text style={styles.title}>
                    CSV
                </Text>

                <Button
                    title='ЕКСПОРТ У CSV'
                    onPress={
                        exportCSV
                    }
                />

            </View>

            <View style={styles.bottom} />

        </ScrollView>
    )
}


const styles = StyleSheet.create({

    page: {
        flex: 1,
        backgroundColor: '#121212',
        paddingHorizontal: 20,
        paddingTop: 20,
        width: '100%',
        maxWidth: 1100,
        alignSelf: 'center'
    },

    mainTitle: {
        color: '#fff',
        fontSize: 34,
        fontWeight: 'bold',
        textAlign: 'center',
        marginTop: 20,
        marginBottom: 30,
        letterSpacing: 2
    },

    block: {
        backgroundColor: '#202020',
        padding: 24,
        marginBottom: 22,
        borderRadius: 14,
        borderWidth: 1,
        borderColor: '#303030',
        width: '100%'
    },

    title: {
        color: '#fff',
        fontSize: 22,
        fontWeight: 'bold',
        marginBottom: 18
    },

    image: {
        width: '100%',
        maxWidth: 700,
        height: 380,
        resizeMode: 'contain',
        marginTop: 20,
        alignSelf: 'center',
        backgroundColor: '#111',
        borderRadius: 12
    },

    input: {
        backgroundColor: '#fff',
        color: '#111',
        paddingHorizontal: 15,
        paddingVertical: 13,
        marginTop: 12,
        marginBottom: 12,
        borderRadius: 8,
        fontSize: 16
    },

    historyItem: {
        backgroundColor: '#292929',
        borderWidth: 1,
        borderColor: '#383838',
        padding: 16,
        marginTop: 12,
        borderRadius: 10
    },

    historyText: {
        color: '#fff',
        fontSize: 16,
        marginBottom: 8
    },

    resultBlock: {
        backgroundColor: '#f5f5f5',
        padding: 24,
        marginBottom: 22,
        borderRadius: 14,
        width: '100%'
    },

    resultTitle: {
        color: '#111',
        fontSize: 24,
        fontWeight: 'bold',
        marginBottom: 18
    },

    resultBird: {
        color: '#111',
        fontSize: 28,
        fontWeight: 'bold',
        marginBottom: 10
    },

    resultText: {
        color: '#222',
        fontSize: 17,
        marginBottom: 8
    },

    resultSubTitle: {
        color: '#111',
        fontSize: 20,
        fontWeight: 'bold',
        marginTop: 20,
        marginBottom: 12
    },

    stats: {
        backgroundColor: '#f5f5f5',
        padding: 20,
        marginTop: 18,
        borderRadius: 10,
        gap: 10
    },

    statsText: {
        color: '#111',
        fontSize: 17
    },

    space: {
        height: 18
    },

    bottom: {
        height: 60
    }
})
