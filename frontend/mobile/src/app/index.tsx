import { useState } from 'react'

import {
    View,
    Text,
    Button,
    Image,
    ScrollView,
    StyleSheet,
    TextInput,
    Alert
} from 'react-native'

import * as ImagePicker from 'expo-image-picker'

import { fetch } from 'expo/fetch'
import { File } from 'expo-file-system'


const API = 'http://192.168.0.100:8000'


type BirdResult = {
    species: string
    confidence: number
}


type AnalyzeResult = {
    id: number
    image_name: string
    best_result: BirdResult
    top_3: BirdResult[]
}


type HistoryItem = {
    id: number
    image_name: string
    predicted_species: string
    confidence: number
    analysis_date: string
}


export default function App() {

    const [image, setImage] =
        useState<ImagePicker.ImagePickerAsset | null>(null)

    const [result, setResult] =
        useState<AnalyzeResult | null>(null)

    const [history, setHistory] =
        useState<HistoryItem[]>([])

    const [search, setSearch] =
        useState('')

    const [stats, setStats] =
        useState<any>(null)

    const [loading, setLoading] =
        useState(false)


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

        if (!image) {

            Alert.alert(
                'Помилка',
                'Спочатку оберіть фотографію'
            )

            return
        }

        setLoading(true)

        try {

            const file =
                new File(image.uri)

            const formData =
                new FormData()

            formData.append(
                'file',
                file
            )


            const response =
                await fetch(
                    `${API}/analyze`,
                    {
                        method: 'POST',
                        body: formData,
                        headers: {
                            Accept: 'application/json'
                        }
                    }
                )


            const text =
                await response.text()


            if (!response.ok) {

                Alert.alert(
                    'Помилка backend',
                    `${response.status}\n${text}`
                )

                return
            }


            const data =
                JSON.parse(text)


            setResult(data)

            await loadHistory()
        }

        catch (error) {

            Alert.alert(
                'Помилка',
                String(error)
            )
        }

        finally {

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
        }

        catch {

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
        }

        catch {

            Alert.alert(
                'Помилка',
                'Не вдалося виконати пошук'
            )
        }
    }


    async function deleteBird(id: number) {

        try {

            await fetch(
                `${API}/birds/${id}`,
                {
                    method: 'DELETE'
                }
            )

            await loadHistory()
        }

        catch {

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
        }

        catch {

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
                        method: 'POST'
                    }
                )

            const data =
                await response.json()

            Alert.alert(
                'CSV',
                `${data.message}\n${data.file}`
            )
        }

        catch {

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
                    Аналіз фотографії
                </Text>


                <Button
                    title='ОБРАТИ ФОТО'
                    onPress={selectPhoto}
                />


                {
                    image &&

                    <Image
                        source={{
                            uri: image.uri
                        }}
                        style={styles.image}
                    />
                }


                <View style={styles.space} />


                <Button
                    title={
                        loading
                            ? 'АНАЛІЗ...'
                            : 'ПРОАНАЛІЗУВАТИ'
                    }
                    onPress={analyzePhoto}
                    disabled={loading}
                />

            </View>


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
                    onPress={loadHistory}
                />


                <TextInput
                    style={styles.input}
                    placeholder='Назва птаха'
                    placeholderTextColor='#777'
                    value={search}
                    onChangeText={setSearch}
                />


                <Button
                    title='ПОШУК'
                    onPress={searchBird}
                />


                {
                    history.map(
                        (item) => (

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
                                    onPress={
                                        () => deleteBird(item.id)
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
                    onPress={loadStatistics}
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
                    onPress={exportCSV}
                />

            </View>


            <View style={styles.bottom} />

        </ScrollView>
    )
}


const styles = StyleSheet.create({

    page: {
        flex: 1,
        backgroundColor: '#171717',
        padding: 20
    },

    mainTitle: {
        color: '#fff',
        fontSize: 30,
        fontWeight: 'bold',
        textAlign: 'center',
        marginTop: 30
    },

    description: {
        color: '#888',
        textAlign: 'center',
        marginBottom: 20
    },

    block: {
        backgroundColor: '#242424',
        padding: 18,
        marginBottom: 20,
        borderRadius: 8
    },

    title: {
        color: '#fff',
        fontSize: 20,
        fontWeight: 'bold',
        marginBottom: 15
    },

    image: {
        width: '100%',
        height: 280,
        resizeMode: 'contain',
        marginTop: 15,
        backgroundColor: '#111'
    },

    input: {
        backgroundColor: '#fff',
        color: '#000',
        padding: 10,
        marginTop: 15,
        marginBottom: 10,
        borderRadius: 5
    },

    historyItem: {
        borderBottomWidth: 1,
        borderBottomColor: '#444',
        paddingVertical: 12,
        marginTop: 5
    },

    historyText: {
        color: '#fff',
        marginBottom: 5
    },

    resultBlock: {
        backgroundColor: '#fff',
        padding: 18,
        marginBottom: 20,
        borderRadius: 8
    },

    resultTitle: {
        color: '#000',
        fontSize: 20,
        fontWeight: 'bold',
        marginBottom: 20
    },

    resultBird: {
        color: '#000',
        fontSize: 22,
        fontWeight: 'bold',
        marginBottom: 8
    },

    resultText: {
        color: '#000',
        fontSize: 16,
        marginBottom: 8
    },

    resultSubTitle: {
        color: '#000',
        fontSize: 18,
        fontWeight: 'bold',
        marginTop: 18,
        marginBottom: 10
    },

    stats: {
        backgroundColor: '#fff',
        padding: 15,
        marginTop: 15,
        borderRadius: 5,
        gap: 8
    },

    statsText: {
        color: '#000',
        fontSize: 16
    },

    space: {
        height: 15
    },

    bottom: {
        height: 50
    }

})